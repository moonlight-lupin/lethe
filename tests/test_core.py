"""Assertion-based unit tests for the detection / tokenisation / restore core
and the OOXML string redaction — the trust-critical paths.

Runs under pytest (`pytest tests/test_core.py`) or directly
(`python tests/test_core.py`). Uses an isolated, temporary data dir so the
vault test never touches the user's real entities.json / vault/.
"""
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Isolate all on-disk state (vault, dictionary) BEFORE importing the package.
os.environ["LETHE_DATA_DIR"] = os.path.join(tempfile.gettempdir(), "lethe_test_core_data")

from lethe import (Entity, assign_tokens, build_replacer, build_restorer,
                   detect, extract_text, redact_document, vault)


def _redact(text, ents, **kw):
    items = assign_tokens(detect(text, ents, **kw))
    repl, t2r = build_replacer(items)
    out, _ = repl(text)
    return out, items, t2r


# ---- overlapping aliases: longest surface wins, all map to one token --------
def test_overlapping_aliases():
    ents = [Entity("Acme Capital Partners", "COUNTERPARTY", ["Acme", "ACP"])]
    text = "Acme Capital Partners (Acme, ACP) closed the deal; Acme led."
    out, items, _ = _redact(text, ents, enable_suggestions=False)
    assert "Acme" not in out and "ACP" not in out, out
    # one entity → one token, every surface mapped to it
    assert out.count("[COUNTERPARTY_001]") == 4, out
    assert len(items) == 1


# ---- pattern vs name overlap: the longer email span wins inside it ----------
def test_email_name_overlap():
    ents = [Entity("Acme", "COUNTERPARTY", [])]
    text = "Acme at info@acme.com today"
    out, _, _ = _redact(text, ents)
    assert "[COUNTERPARTY_001]" in out          # the standalone "Acme"
    assert "[EMAIL_001]" in out                  # the whole email, not shredded
    assert "acme.com" not in out and "@" not in out, out


# ---- CJK names: substring match (no word boundaries in CJK) -----------------
def test_cjk_substring_match():
    ents = [Entity("李伟", "PERSON", []), Entity("明德资本", "COUNTERPARTY", [])]
    text = "客户是李伟先生，代表明德资本出席。"
    out, _, _ = _redact(text, ents, enable_suggestions=False)
    assert "李伟" not in out and "明德资本" not in out, out
    assert "[PERSON_001]" in out and "[COUNTERPARTY_001]" in out


# ---- stable tokens: the same name always maps to the same token -------------
def test_stable_tokens():
    ents = [Entity("John Smith", "PERSON", []), Entity("Acme", "COUNTERPARTY", [])]
    out, _, _ = _redact("John Smith met John Smith from Acme.", ents,
                        enable_suggestions=False)
    assert out.count("[PERSON_001]") == 2 and "[COUNTERPARTY_001]" in out


# ---- custom token type tokenises as [PROJECT_001] ---------------------------
def test_custom_token_type():
    ents = [Entity("Project Atlas", "PROJECT", [])]
    out, _, _ = _redact("Project Atlas kicked off.", ents, enable_suggestions=False)
    assert "[PROJECT_001]" in out and "Project Atlas" not in out


# ---- restore is EXACT: an AI-mangled token is left alone --------------------
def test_restore_exact_match():
    restore = build_restorer({"[PERSON_001]": "John Smith"})
    ok, n = restore("Summary by [PERSON_001] and again [PERSON_001].")
    assert n == 2 and ok.count("John Smith") == 2
    # token the AI altered (space for underscore, or lower-cased) is NOT restored
    bad, n2 = restore("Summary by [PERSON 001] / [person_001].")
    assert n2 == 0 and "John Smith" not in bad


# ---- vault round-trip + wrong-passphrase guard ------------------------------
def test_vault_roundtrip_and_wrong_passphrase():
    mapping = {"[PERSON_001]": "John Smith", "[COUNTERPARTY_001]": "Acme Capital Partners"}
    jid = "test-job-0001"
    vault.save_job(jid, mapping, "correct horse", meta={"source_file": "x", "replacements": 2})
    got = vault.load_job(jid, "correct horse")
    assert got["mapping"] == mapping
    raised = False
    try:
        vault.load_job(jid, "wrong passphrase")
    except (ValueError, Exception):
        raised = True
    assert raised, "wrong passphrase must not decrypt the job"
    vault.delete_job(jid)


# ---- Excel: shared-string cells (a separate xl/sharedStrings.xml, the <si>
# path, which is what Excel itself writes — openpyxl now emits inline strings) -
def _shared_string_xlsx(values):
    """Minimal .xlsx with a real shared-strings table: row-1 cells (A1, B1, …)
    reference string indices via t='s', exercising _redact_xlsx's <si> path."""
    sst = "".join(f"<si><t>{v}</t></si>" for v in values)
    cells = "".join(
        f'<c r="{chr(65 + i)}1" t="s"><v>{i}</v></c>' for i in range(len(values)))
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    parts = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{R}/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'xmlns:r="{R}"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{R}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{R}/sharedStrings" Target="sharedStrings.xml"/>'
            '</Relationships>',
        "xl/sharedStrings.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{len(values)}" uniqueCount="{len(values)}">{sst}</sst>',
        "xl/worksheets/sheet1.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData><row r="1">{cells}</row></sheetData></worksheet>',
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_xlsx_shared_strings():
    data = _shared_string_xlsx(["John Smith", "Acme Capital Partners"])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert "xl/sharedStrings.xml" in z.namelist()   # the <si> path, for real
    ents = [Entity("John Smith", "PERSON", []),
            Entity("Acme Capital Partners", "COUNTERPARTY", [])]
    text = extract_text(data, "xlsx")
    assert "John Smith" in text and "Acme Capital Partners" in text, "shared strings unreadable"
    repl, _ = build_replacer(assign_tokens(detect(text, ents, enable_suggestions=False)))
    out, ext, hits = redact_document(data, "xlsx", repl)
    out_text = extract_text(out, "xlsx")
    assert ext == ".xlsx" and hits >= 2
    assert "John Smith" not in out_text and "Acme Capital Partners" not in out_text
    assert "[PERSON_001]" in out_text and "[COUNTERPARTY_001]" in out_text


# ---- Excel: inline-string cells (t='inlineStr', which openpyxl now emits) ----
def _inline_string_xlsx(cells):
    """Build a minimal valid .xlsx whose cells are inline strings (t='inlineStr'),
    which openpyxl never emits — exercising _redact_xlsx's <is> path."""
    row = "".join(
        f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>' for ref, val in cells)
    parts = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        "xl/worksheets/sheet1.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData><row r="1">{row}</row></sheetData></worksheet>',
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_xlsx_inline_strings():
    data = _inline_string_xlsx([("A1", "John Smith"), ("B1", "Acme Capital Partners")])
    ents = [Entity("John Smith", "PERSON", []),
            Entity("Acme Capital Partners", "COUNTERPARTY", [])]
    text = extract_text(data, "xlsx")
    assert "John Smith" in text and "Acme Capital Partners" in text, "inline strings unreadable"
    repl, _ = build_replacer(assign_tokens(detect(text, ents, enable_suggestions=False)))
    out, ext, hits = redact_document(data, "xlsx", repl)
    out_text = extract_text(out, "xlsx")
    assert ext == ".xlsx" and hits >= 2
    assert "John Smith" not in out_text and "Acme Capital Partners" not in out_text
    assert "[PERSON_001]" in out_text and "[COUNTERPARTY_001]" in out_text


# ---- the PDF notice adapts to whether OCR ran (no more stale "there is no OCR")
def test_pdf_notice_is_conditional():
    from docx import Document
    from lethe import docio

    def notice_text(pages):
        doc = Document()
        docio._add_notice_header(doc, pages)
        return "\n".join(p.text for p in doc.paragraphs)

    # text-only page: generic "rendered as pixels" note, no OCR/unread claims
    t = notice_text([{"n": 1, "narrative": "x", "tables": [], "n_words": 50,
                      "n_images": 0, "ocr": False}])
    assert "recovered with local OCR" not in t and "could NOT be read" not in t
    # an OCR'd page is named as recovered-by-OCR / review
    t2 = notice_text([{"n": 2, "narrative": "y", "tables": [], "n_words": 30,
                       "n_images": 1, "ocr": True}])
    assert "Page(s) 2" in t2 and "local OCR" in t2
    # an unread image-only page is named as NOT redacted
    t3 = notice_text([{"n": 3, "narrative": "", "tables": [], "n_words": 0,
                       "n_images": 1, "ocr": False}])
    assert "Page(s) 3" in t3 and "could NOT be read" in t3


# ---- OCR never fires (or downloads) when no model is present locally --------
def test_ocr_skips_without_local_model():
    from lethe import docio
    # Simulate "no OCR model on disk" directly so the test is hermetic regardless
    # of what other tests have downloaded into the shared data dir.
    orig = docio.installed_ocr_languages
    docio.installed_ocr_languages = lambda: []
    try:
        pages = [{"n": 1, "narrative": "", "tables": [], "n_words": 0,
                  "n_images": 1, "ocr": False}]
        docio._merge_ocr(b"%PDF-not-real", pages)   # no model → no OCR, no fetch, no-op
        assert pages[0]["ocr"] is False and pages[0]["narrative"] == ""
    finally:
        docio.installed_ocr_languages = orig


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"CORE OK — {len(fns)} tests passed")
