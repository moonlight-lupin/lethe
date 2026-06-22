---
name: testing-and-ci
description: How Lethe's tests are structured and run (pytest + GitHub Actions CI), plus an openpyxl gotcha
metadata:
  type: project
---

Tests live in `tests/`. They run two ways: directly (`python tests/test_x.py`, the
original style — module-level asserts + prints) and under **pytest** (`pytest tests/`),
which CI uses. For pytest collection to stay clean, a test file must NOT call
`sys.exit()` at module level — `tests/test_ocr_pdf.py` was refactored into a
`def test_ocr_pdf()` that skips via early `return` (and guards its fpdf/Pillow imports)
for exactly this reason. `tests/test_core.py` is the canonical pytest file (function-based,
isolates the vault by setting `LETHE_DATA_DIR` to a temp dir before importing the package).

**CI:** `.github/workflows/ci.yml` runs `pip install -e .[dev]` + `pytest tests/` on
ubuntu-latest **and** windows-latest for every push to main / PR. The `[dev]` extra is just
pytest; the optional `[nlp]/[ocr]/[email]` engines aren't installed in CI (kept fast), so
`test_ocr_pdf` self-skips there and `test_email` covers only `.eml`/`.html`.

**Gotcha:** modern **openpyxl writes INLINE strings, not a shared-strings table** — a
`Workbook().save()` produces no `xl/sharedStrings.xml`. Real Excel files DO use shared
strings, and `_redact_xlsx` handles both (`<si>` shared + `<is>` inline). So to test the
shared-strings (`si`) redaction path you must hand-craft the .xlsx (see
`_shared_string_xlsx` in test_core); openpyxl alone only exercises the inline path.
Docs/CI updates follow [[keep-docs-in-sync]].
