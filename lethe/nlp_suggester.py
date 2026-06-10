"""
Optional NLP-based name/organisation suggester (Microsoft Presidio + spaCy),
with on-demand, per-language model downloads.

Ships with English only (small). Extra languages (Chinese, Japanese, Korean, …)
are downloaded by the user from the Settings page when needed -- so the bundle
stays small but can expand. Downloaded models are detected by script: a Chinese
model only runs on text that actually contains Chinese characters, etc.

This powers the *suggestion* lane only -- candidate people and counterparties not
already in the dictionary, surfaced for the human reviewer. It never auto-redacts.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from functools import lru_cache

_BASE = "https://github.com/explosion/spacy-models/releases/download"

# Each language: spaCy model + the unicode ranges that imply "this script is
# present in the text" (None = always run when installed, e.g. Latin scripts).
# "ocr" lists the Tesseract model code(s) downloaded alongside the spaCy model so
# that adding a language enables BOTH name detection and OCR for that script.
# English ("eng") ships bundled offline, so it carries no download here. "size" is
# the COMBINED download (spaCy model + OCR model): zh = 48 + 24 (chi_sim+chi_tra),
# ja = 70 + 14 (jpn), ko = 36 + 12 (kor).
LANGUAGES = [
    {"code": "en", "label": "English", "model": "en_core_web_sm", "version": "3.8.0",
     "builtin": True, "ranges": None, "size": "built-in", "ocr": []},
    {"code": "zh", "label": "Chinese", "model": "zh_core_web_sm", "version": "3.8.0",
     "builtin": False, "ranges": [(0x3400, 0x9FFF), (0xF900, 0xFAFF)], "size": "~72 MB",
     "ocr": ["chi_sim", "chi_tra"]},
    {"code": "ja", "label": "Japanese", "model": "ja_core_news_sm", "version": "3.8.0",
     "builtin": False, "ranges": [(0x3040, 0x30FF), (0x4E00, 0x9FFF), (0xFF66, 0xFF9F)], "size": "~84 MB",
     "ocr": ["jpn"]},
    {"code": "ko", "label": "Korean", "model": "ko_core_news_sm", "version": "3.8.0",
     "builtin": False, "ranges": [(0xAC00, 0xD7AF)], "size": "~48 MB", "ocr": ["kor"]},
]


def _wheel_url(lang: dict) -> str:
    m, v = lang["model"], lang["version"]
    return f"{_BASE}/{m}-{v}/{m}-{v}-py3-none-any.whl"


def _ranges_re(ranges):
    if not ranges:
        return None
    return re.compile("[" + "".join(f"\\u{a:04x}-\\u{b:04x}" for a, b in ranges) + "]")


for _lang in LANGUAGES:
    _lang["_re"] = _ranges_re(_lang["ranges"])

_PRESIDIO_TO_TYPE = {"PERSON": "PERSON", "ORGANIZATION": "COUNTERPARTY"}
_NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    "ner_model_configuration": {
        "model_to_presidio_entity_mapping": {
            "PER": "PERSON", "PERSON": "PERSON", "ORG": "ORGANIZATION", "FAC": "ORGANIZATION"},
        "low_confidence_score_multiplier": 0.4,
        "low_score_entity_names": [],
    },
}


# ---- install / download ------------------------------------------------------
def is_installed(model: str) -> bool:
    try:
        return importlib.util.find_spec(model) is not None
    except (ImportError, ValueError):
        return False


def available() -> bool:
    """The suggester as a whole is usable if Presidio + the English model exist."""
    try:
        import presidio_analyzer  # noqa: F401
        import spacy  # noqa: F401
    except Exception:
        return False
    return is_installed("en_core_web_sm")


def language_status() -> list[dict]:
    return [{"code": L["code"], "label": L["label"], "model": L["model"], "size": L["size"],
             "builtin": L["builtin"], "installed": is_installed(L["model"]),
             "ocr": list(L["ocr"])}
            for L in LANGUAGES]


def download_language(code: str) -> tuple[bool, str]:
    """pip-install a language model wheel into this Python. Needs internet.
    Returns (ok, log_tail)."""
    lang = next((L for L in LANGUAGES if L["code"] == code), None)
    if lang is None:
        return False, f"Unknown language: {code}"
    if lang["builtin"]:
        return True, "Built-in."
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-warn-script-location",
             "--disable-pip-version-check", _wheel_url(lang)],
            capture_output=True, text=True, timeout=900)
    except Exception as exc:  # noqa: BLE001
        return False, f"Download failed: {exc}"
    importlib.invalidate_caches()
    _spacy_model.cache_clear()
    ok = proc.returncode == 0
    log = (proc.stdout + "\n" + proc.stderr).strip()
    return ok, log[-1500:]


def remove_language(code: str) -> tuple[bool, str]:
    """Uninstall a downloaded language model. The built-in English one can't be
    removed. Returns (ok, log_tail)."""
    lang = next((L for L in LANGUAGES if L["code"] == code), None)
    if lang is None:
        return False, f"Unknown language: {code}"
    if lang["builtin"]:
        return False, "The built-in English model can't be removed."
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", lang["model"]],
            capture_output=True, text=True, timeout=300)
    except Exception as exc:  # noqa: BLE001
        return False, f"Remove failed: {exc}"
    importlib.invalidate_caches()
    _spacy_model.cache_clear()
    ok = proc.returncode == 0
    return ok, (proc.stdout + "\n" + proc.stderr).strip()[-1500:]


# ---- detection ---------------------------------------------------------------
@lru_cache(maxsize=1)
def _analyzer():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    nlp_engine = NlpEngineProvider(nlp_configuration=_NLP_CONFIG).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])


@lru_cache(maxsize=4)
def _spacy_model(model: str):
    import spacy
    return spacy.load(model)


def _presidio_en(text: str, min_score: float) -> list[tuple[int, int, str]]:
    try:
        results = _analyzer().analyze(text=text, language="en",
                                      entities=["PERSON", "ORGANIZATION"], score_threshold=min_score)
    except Exception:
        return []
    out = []
    for r in results:
        t = _PRESIDIO_TO_TYPE.get(r.entity_type)
        if t:
            out.append((r.start, r.end, t))
    return out


def _spacy_lang(text: str, model: str) -> list[tuple[int, int, str]]:
    try:
        nlp = _spacy_model(model)
    except Exception:
        return []
    out = []
    for ent in nlp(text).ents:
        lab = ent.label_.upper()
        if "PER" in lab:
            t = "PERSON"
        elif "ORG" in lab or "COMP" in lab or lab == "FAC":
            t = "COUNTERPARTY"
        else:
            continue
        out.append((ent.start_char, ent.end_char, t))
    return out


def suggest(text: str, min_score: float = 0.40) -> list[tuple[int, int, str]]:
    """Return [(start, end, internal_type)] candidate people/organisations,
    across English plus any installed language whose script is present."""
    if not text.strip():
        return []
    spans: list[tuple[int, int, str]] = []
    if is_installed("en_core_web_sm"):
        spans += _presidio_en(text, min_score)
    for L in LANGUAGES:
        if L["builtin"] or not is_installed(L["model"]):
            continue
        if L["_re"] is None or L["_re"].search(text):
            spans += _spacy_lang(text, L["model"])
    # de-duplicate identical spans (different models may agree)
    seen, out = set(), []
    for s, e, t in spans:
        if (s, e) not in seen:
            seen.add((s, e))
            out.append((s, e, t))
    return out
