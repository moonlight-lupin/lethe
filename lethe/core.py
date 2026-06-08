"""
Detection + redaction core.

Strategy (in order of reliability for a compliance gate):
  1. Known-entity dictionary  -- your real people / counterparties + aliases.
     Deterministic, ~100% recall on the names that actually matter.
  2. Pattern detectors        -- emails, phone numbers, account/IBAN-like IDs.
  3. Heuristic name suggester -- flags Capitalised multi-word phrases that look
     like names but are NOT in your dictionary, so the reviewer can catch gaps.
     (Best-effort only; the human review step is the real safety net.)

Everything funnels into a list of "items" that the UI presents for human
confirmation before anything is written out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---- token formatting --------------------------------------------------------
# Descriptive placeholders survive a round-trip through an LLM well: the model
# treats "[PERSON_001]" as an opaque placeholder and preserves it verbatim.
TYPE_PREFIX = {
    "PERSON": "PERSON",
    "COUNTERPARTY": "COUNTERPARTY",
    "ORG": "COUNTERPARTY",
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "ACCOUNT": "ACCOUNT",
}


def make_token(entity_type: str, index: int) -> str:
    prefix = TYPE_PREFIX.get(entity_type.upper(), entity_type.upper())
    return f"[{prefix}_{index:03d}]"


# ---- pattern detectors -------------------------------------------------------
PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    # Loose international phone matcher: +65 6789 1234, (02) 1234-5678, etc.
    # Word-boundary lookarounds only (a trailing "." ends a sentence, not the number).
    "PHONE": re.compile(r"(?<!\w)\+?\d[\d\s().\-]{6,}\d(?!\w)"),
    # IBAN-ish / long account numbers (>=8 digits, optional grouping)
    "ACCOUNT": re.compile(r"\b(?:[A-Z]{2}\d{2}[A-Z0-9]{10,30}|\d[\d\- ]{6,}\d)\b"),
}

# Heuristic: 1-4 Capitalised tokens on a single line, allowing common entity
# suffixes. Uses [ \t] (not \s) so a candidate never spans a line break.
_NAME_CANDIDATE = re.compile(
    r"\b([A-Z][a-zA-Z&.\-']+(?:[ \t]+(?:[A-Z][a-zA-Z&.\-']+|of|and|the|de|van|von|bin|binte))*"
    r"(?:[ \t]+(?:Ltd|Limited|LLC|LLP|Inc|Corp|Pte|Plc|GmbH|AG|SA|NV|Co|Fund|Capital|Partners|Holdings))?)\b"
)

# Words we never want to treat as a name candidate on their own.
_STOPWORDS = {
    "The", "This", "That", "These", "Those", "From", "Dear", "Sincerely", "Regards",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday", "Subject", "Re", "To", "Attn",
}


@dataclass
class Entity:
    """A known person or counterparty from the user's dictionary."""
    canonical: str
    type: str  # PERSON | COUNTERPARTY
    aliases: list[str] = field(default_factory=list)

    def surfaces(self) -> list[str]:
        seen, out = set(), []
        for s in [self.canonical, *self.aliases]:
            s = s.strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out


@dataclass
class Item:
    """A confirmed-or-candidate redaction target shown in the review UI."""
    type: str
    canonical: str          # value the token maps back to (the "real" value)
    surfaces: list[str]     # every string form that should be replaced
    source: str             # "dictionary" | "pattern" | "suggestion"
    count: int = 0
    include: bool = True
    token: str = ""


# Hiragana/Katakana, CJK ideographs (+ext A), Hangul, compatibility & half-width.
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿ｦ-ﾟ]")


def _whole_word_regex(surface: str) -> re.Pattern:
    # Names can contain regex metachars (e.g. ".", "&"); escape them.
    body = re.escape(surface)
    if _CJK_RE.search(surface):
        # CJK/Japanese/Korean text has no word delimiters, so word-boundary
        # lookarounds would miss names embedded in running text -> substring match.
        return re.compile(body)
    # \b doesn't work well around &/. so guard with lookarounds on word chars.
    return re.compile(rf"(?<![\w]){body}(?![\w])", re.IGNORECASE)


# Overlap resolution happens in two phases:
#   - "primary" sources (dictionary + pattern) are all MUST-redact. Among them the
#     longest span wins, so a whole-email pattern beats a dictionary name that
#     happens to sit inside it. Dictionary breaks length ties.
#   - "suggestion" spans are candidates (off by default); they only fill regions
#     no primary span claimed, so an unchecked suggestion can never shadow and
#     silently un-redact a real dictionary/pattern hit.
_TIER = {"dictionary": 2, "pattern": 1}
_TYPE_RANK = {"EMAIL": 4, "ACCOUNT": 3, "PHONE": 2}  # account/email beat phone on a tie


@dataclass
class _Span:
    start: int
    end: int
    type: str
    canonical: str
    surface: str
    source: str

    @property
    def length(self) -> int:
        return self.end - self.start


def _regex_suggestions(text: str) -> list[_Span]:
    """Fallback name suggester (people only) when NER isn't available."""
    out: list[_Span] = []
    for m in _NAME_CANDIDATE.finditer(text):
        cand = m.group(1).strip().rstrip(".,;:")
        if not cand:
            continue
        if cand.split()[0] in _STOPWORDS:
            continue
        if len(cand.split()) == 1 and not re.search(
            r"(Ltd|Limited|LLC|LLP|Inc|Corp|Pte|Plc|GmbH|Fund|Capital|Partners|Holdings)$", cand):
            continue
        start = m.start(1)
        out.append(_Span(start, start + len(cand), "PERSON", cand, cand, "suggestion"))
    return out


# Japanese company-name detector. The spaCy JA model often mislabels companies
# (e.g. tags a 株式会社 as EVENT), so we catch them by their legal-form suffix /
# prefix directly. \uXXXX escapes work inside re patterns even in raw strings.
# Name body = Katakana, Kanji, half-width kana, Latin, full-width Latin/digits,
# digits, middle-dot, long-vowel mark -- but NOT Hiragana, so grammatical
# particles (は/が/の…) cleanly bound the company name.
_JP_BODY = r"[゠-ヿ㐀-鿿ｦ-ﾟA-Za-zＡ-Ｚａ-ｚ0-9０-９・ー]"
_JP_SUFFIX = (r"株式会社|合同会社|有限会社|"
              r"合資会社|合名会社|（株）|\(株\)|㈱")
_JP_PREFIX = (r"株式会社|合同会社|有限会社|"
              r"合資会社|合名会社")
_JP_COMPANY = re.compile(
    rf"(?:{_JP_BODY}{{1,24}}(?:{_JP_SUFFIX}))|(?:(?:{_JP_PREFIX}){_JP_BODY}{{1,24}})")


def _jp_company_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _JP_COMPANY.finditer(text)]


def _suggestion_spans(text: str) -> list[_Span]:
    """NLP suggestions (Presidio+spaCy if installed, else the regex heuristic)
    plus the Japanese company-suffix detector (always on)."""
    out: list[_Span] = []
    used_nlp = False
    try:
        from . import nlp_suggester
        if nlp_suggester.available():
            used_nlp = True
            for s, e, t in nlp_suggester.suggest(text):
                surface = text[s:e].rstrip(".,;:")
                if surface:
                    out.append(_Span(s, s + len(surface), t, surface, surface, "suggestion"))
    except Exception:
        used_nlp = False
    if not used_nlp:
        out.extend(_regex_suggestions(text))
    for s, e in _jp_company_spans(text):
        surface = text[s:e]
        if surface:
            out.append(_Span(s, e, "COUNTERPARTY", surface, surface, "suggestion"))
    return out


def detect(text: str, entities: list[Entity], enable_patterns: bool = True,
           enable_suggestions: bool = True) -> list[Item]:
    """Span-based detection with overlap resolution, grouped into review items."""
    spans: list[_Span] = []

    # 1. Dictionary entities --------------------------------------------------
    for ent in entities:
        for s in ent.surfaces():
            for m in _whole_word_regex(s).finditer(text):
                spans.append(_Span(m.start(), m.end(), ent.type, ent.canonical, s, "dictionary"))

    # 2. Pattern detectors ----------------------------------------------------
    if enable_patterns:
        for ptype, pat in PATTERNS.items():
            for m in pat.finditer(text):
                v = m.group(0).strip()
                if not v:
                    continue
                if ptype == "PHONE" and sum(c.isdigit() for c in v) < 7:
                    continue
                # account: require enough digits to avoid catching years etc.
                if ptype == "ACCOUNT" and sum(c.isdigit() for c in v) < 8:
                    continue
                start = m.start() + m.group(0).find(v)
                spans.append(_Span(start, start + len(v), ptype, v, v, "pattern"))

    # 3. Name / organisation suggestions -------------------------------------
    #    Prefer Presidio+spaCy NER when available (people AND counterparties);
    #    otherwise fall back to the built-in regex heuristic (people only).
    if enable_suggestions:
        spans.extend(_suggestion_spans(text))

    # ---- phase 1: resolve primary (dictionary + pattern) by longest-wins ----
    def _overlaps(sp: _Span, taken: list[tuple[int, int]]) -> bool:
        return any(sp.start < e and s < sp.end for s, e in taken)

    primary = [s for s in spans if s.source != "suggestion"]
    primary.sort(key=lambda s: (s.length, _TIER[s.source], _TYPE_RANK.get(s.type, 0)), reverse=True)
    accepted: list[_Span] = []
    taken: list[tuple[int, int]] = []
    for sp in primary:
        if _overlaps(sp, taken):
            continue
        accepted.append(sp)
        taken.append((sp.start, sp.end))

    # ---- phase 2: suggestions only fill regions no primary span claimed -----
    suggestions = [s for s in spans if s.source == "suggestion"]
    suggestions.sort(key=lambda s: s.length, reverse=True)
    for sp in suggestions:
        if _overlaps(sp, taken):
            continue
        accepted.append(sp)
        taken.append((sp.start, sp.end))

    # ---- group accepted spans into items by canonical value ----------------
    groups: dict[tuple[str, str], Item] = {}
    order: list[tuple[str, str]] = []
    for sp in accepted:
        key = (sp.source if sp.source != "dictionary" else "dictionary", sp.canonical)
        if key not in groups:
            groups[key] = Item(type=sp.type, canonical=sp.canonical, surfaces=[],
                               source=sp.source, count=0,
                               include=(sp.source != "suggestion"))
            order.append(key)
        it = groups[key]
        it.count += 1
        if sp.surface not in it.surfaces:
            it.surfaces.append(sp.surface)

    items = [groups[k] for k in order]
    # stable, readable ordering: dictionary, then patterns, then suggestions
    rank = {"dictionary": 0, "pattern": 1, "suggestion": 2}
    items.sort(key=lambda it: (rank[it.source], -it.count, it.canonical.lower()))
    return items


def assign_tokens(items: list[Item]) -> list[Item]:
    """Allocate stable, per-type, sequential tokens to the included items."""
    counters: dict[str, int] = {}
    for it in items:
        if not it.include:
            it.token = ""
            continue
        key = TYPE_PREFIX.get(it.type.upper(), it.type.upper())
        counters[key] = counters.get(key, 0) + 1
        it.token = make_token(it.type, counters[key])
    return items


def build_replacer(items: list[Item]):
    """
    Build a single function that redacts text using all included items.
    Longest surfaces first so "John Smith" wins over "Smith".
    Returns (replace_fn, token_to_canonical).
    """
    pairs: list[tuple[re.Pattern, str]] = []
    token_to_real: dict[str, str] = {}
    surface_token: list[tuple[str, str]] = []
    for it in items:
        if not it.include or not it.token:
            continue
        token_to_real[it.token] = it.canonical
        for s in it.surfaces:
            surface_token.append((s, it.token))
    # longest first
    surface_token.sort(key=lambda st: len(st[0]), reverse=True)
    for s, tok in surface_token:
        pairs.append((_whole_word_regex(s), tok))

    def replace(text: str) -> tuple[str, int]:
        hits = 0
        for pat, tok in pairs:
            text, n = pat.subn(tok, text)
            hits += n
        return text, hits

    return replace, token_to_real


def build_restorer(token_to_real: dict[str, str]):
    """Inverse: swap tokens in AI output back to real values."""
    # Longest tokens first (defensive; tokens are uniform but be safe).
    toks = sorted(token_to_real, key=len, reverse=True)
    pats = [(re.compile(re.escape(t)), token_to_real[t]) for t in toks]

    def restore(text: str) -> tuple[str, int]:
        hits = 0
        for pat, real in pats:
            text, n = pat.subn(real, text)
            hits += n
        return text, hits

    return restore
