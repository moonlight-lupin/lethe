# Lethe — Roadmap

## Shipped

- **v1.0.0** — Word/PDF/Excel de-identification with an entity dictionary,
  Presidio+spaCy suggestions, encrypted reversible vault, custom token types,
  table-aware PDF→Word with `Page N` anchors, xlsx OOXML-surgery redaction,
  cross-platform pipx install + Windows installer.

- **v1.1.0** — **PowerPoint (.pptx)** support (format-preserving via
  `python-pptx`: slide text incl. grouped shapes, tables, speaker notes,
  master/layout); **local OCR for scanned/image PDF pages** via
  [run-llama/liteparse](https://github.com/run-llama/liteparse) (PDFium +
  Tesseract, Apache-2.0, fully offline) — pdfplumber keeps native text + table
  grids, liteparse selectively OCRs only image-based pages and the recovered
  text flows through normal detection/redaction, marked "review carefully".
  Optional `lethe[ocr]` extra; bundled in the Windows build.

- **v1.2.0** — **Restore tab** (manual re-identify for documents tokenised
  outside Lethe, with explicit per-token Type + Save controls; doubles as a
  template filler); **Settings → Files & folders** (locate/open the data and
  program folders).

- **v1.3.0** — **Email ingestion** (`.eml` / Outlook `.msg` / `.html` → a
  de-identified Word file; the From/To/Cc/Subject header block is redacted with
  the body). `.eml`/`.html` use the stdlib; `.msg` is the optional `lethe[email]`
  extra, bundled in the Windows build.

## Later / undecided

- **More one-way ingest** (EPUB, and other formats not yet covered) — de-identified
  Word/Markdown out, not the original format back. The native `.eml`/`.msg`/`.html`
  path covers email; [microsoft/markitdown](https://github.com/microsoft/markitdown)
  (MIT) is a candidate engine for the rest, with its Azure OCR paths kept disabled
  (cloud calls would violate the local-only promise).

- **Machine-readable page-map sidecar** for PDF conversions — a small JSON
  mapping text offsets → source PDF page, so downstream tools can cite exact
  pages programmatically instead of parsing the `Page N` headings.

- **Native macOS / Linux double-click apps** — PyInstaller builds in the release
  workflow (GitHub Actions matrix), if pipx proves insufficient for
  non-technical users on those platforms.
