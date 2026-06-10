# Lethe — Roadmap

Shipped in **v1.0.0**: Word/PDF/Excel de-identification with an entity dictionary,
Presidio+spaCy suggestions, encrypted reversible vault, custom token types,
table-aware PDF→Word with `Page N` anchors, xlsx OOXML-surgery redaction,
cross-platform pipx install + Windows installer.

## Done on main (lands in v1.1)

- **PowerPoint (.pptx) support** — format-preserving via `python-pptx`: slide
  text (incl. grouped shapes), tables, speaker notes and master/layout text are
  redacted and a working `.pptx` comes back. Text inside charts/SmartArt is out
  of scope (documented), as is text in images, like everywhere else.

- **Local OCR for scanned / image-based PDF pages** — via
  [run-llama/liteparse](https://github.com/run-llama/liteparse) (PDFium +
  bundled Tesseract, Apache-2.0, ~16 MB, fully offline). Hybrid as planned:
  pdfplumber keeps native text + table grids; liteparse selectively OCRs only
  the image-based pages (`target_pages`), whose recovered text then flows
  through normal detection/redaction and is marked "review carefully" in the
  UI. Optional `lethe[ocr]` extra; included in requirements.txt so the portable
  bundle and dev installs get it. Spike findings: all test names recovered
  verbatim from pixel-only pages, ~0.26 s/page selective, Windows wheel on 3.13.

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
