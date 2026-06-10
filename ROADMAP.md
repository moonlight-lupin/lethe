# Lethe — Roadmap

Shipped in **v1.0.0**: Word/PDF/Excel de-identification with an entity dictionary,
Presidio+spaCy suggestions, encrypted reversible vault, custom token types,
table-aware PDF→Word with `Page N` anchors, xlsx OOXML-surgery redaction,
cross-platform pipx install + Windows installer.

## Next (v1.1 candidates)

- **PowerPoint (.pptx) support** — format-preserving, in the spirit of the docx
  path: walk shapes / text frames / tables with `python-pptx`, replace runs,
  return a working `.pptx`. Decks are dense with counterparty names, so this is
  the highest-value new format. (Slide notes + master/layout text included;
  text inside images stays out of scope, as everywhere.)

- **OCR for scanned / image-based PDF pages** — today Lethe *flags* image pages
  ("names here can't be detected — no OCR"); with a local OCR engine those pages
  could be detected and redacted instead. Candidate:
  [run-llama/liteparse](https://github.com/run-llama/liteparse) — fully local
  (PDFium + bundled Tesseract, Apache-2.0), selective OCR merged with native
  text. **Spike first**: keep pdfplumber for native text + table grids (LiteParse
  doesn't obviously emit structured tables); use LiteParse/Tesseract only for the
  pages we currently warn about. Verify per-page fidelity, OCR quality on real
  scans, Windows wheel availability + bundle size, and fully-offline behaviour.
  OCR output goes through the normal detection + review flow — the review step
  remains the safety net.

## Later / undecided

- **Best-effort ingest of other formats** (HTML, EPUB, Outlook `.msg`) behind an
  optional extra — one-way: de-identified Markdown/Word out, not the original
  format back. [microsoft/markitdown](https://github.com/microsoft/markitdown)
  (MIT) is the likely engine; its Azure OCR paths must stay disabled (cloud
  calls violate the local-only promise). Clearly labelled as one-way.

- **Machine-readable page-map sidecar** for PDF conversions — a small JSON
  mapping text offsets → source PDF page, so downstream tools can cite exact
  pages programmatically instead of parsing the `Page N` headings.

- **Native macOS / Linux double-click apps** — PyInstaller builds in the release
  workflow (GitHub Actions matrix), if pipx proves insufficient for
  non-technical users on those platforms.
