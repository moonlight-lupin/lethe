**Lethe** is a fully-local, reversible document de-identifier — it replaces people and
counterparty names with stable tokens *before* you send a document to an AI, then
restores the real names in the AI's reply. Your documents and the names in them never
leave your machine — no cloud, no API key, no telemetry.

## What's new in 1.3.1 (patch)

A privacy-accuracy and robustness pass — no new formats.

- **Precise privacy promise.** Reworded throughout: your document content and the names
  in it are never transmitted; the *only* network use is downloading an optional
  language/OCR model, and only when you explicitly install one.
- **OCR never downloads silently.** Scanned-page OCR now runs only against models already
  on disk — it will never fetch one over the internet on first use. On a pip install you
  add the English OCR model with one click in **Settings** (the Windows build still bundles
  it); until then, image pages are flagged rather than silently downloading anything.
- **Truthful PDF notice.** The notice in a converted PDF→Word file now names exactly which
  pages were recovered by OCR (review them) and which image-only pages couldn't be read
  (not redacted) — instead of a fixed "there is no OCR" line.
- **Less sensitive data kept in memory.** The parsed-PDF cache is reduced to a single
  document and cleared as soon as a job finishes.
- **Expanded, assertion-based test suite** (overlapping aliases, CJK names, inline/shared
  Excel strings, exact-match restore, vault wrong-passphrase, and more).

### Earlier — 1.3.0

- **Email ingestion (`.eml` / Outlook `.msg` / `.html`)** → a de-identified **Word**
  document, with the **From / To / Cc / Subject** header block redacted along with the
  body. `.eml`/`.html` work out of the box; `.msg` ships in the Windows build and via the
  optional `[email]` pip extra. Attachments and inline images aren't included.

## Install

| You are… | Get it | Run |
|---|---|---|
| **Windows, non-technical** | download the **`…-Setup.exe`** below and run it (per-user, no admin rights) | Start-menu / Desktop shortcut |
| **Windows, portable** | download the **`…-Portable.zip`** below, unzip, run the launcher | data stays inside the folder |
| **Windows / macOS / Linux, with Python 3.10–3.13** | `pipx install "lethe[nlp,ocr,email] @ git+https://github.com/moonlight-lupin/lethe@v1.3.1"` | `lethe` |
| **lean (no extras, smaller)** | `pipx install "git+https://github.com/moonlight-lupin/lethe@v1.3.1"` | `lethe` |

The Windows installer and portable bundle embed their own Python — **no Python needed**
on the target PC, and they include all extras. The `pipx` route is the cross-platform way
for macOS and Linux; `[nlp]` adds the Presidio + spaCy suggestion engine, `[ocr]` adds
scanned-page OCR, and `[email]` adds Outlook `.msg` support (`.eml`/`.html` work without
it). Either way, Lethe opens at `http://localhost:8731`.

## Highlights

- Word / PowerPoint / PDF / Excel / email in, de-identified copies out (same format;
  PDFs and emails → a de-identified Word file with an agent-facing notice header).
- A curated **entity dictionary** is the reliable core; optional NLP **suggestions** and
  pattern detection (emails / phones / accounts) on top.
- **Reversible**: each job's token→name map is encrypted with your passphrase; restore
  the real names into the AI's reply afterwards.
- Custom token types, a spreadsheet table preview, scanned-page OCR with review prompts,
  and a classical light/dark theme.

Released under the **Apache License 2.0**. See the README for full documentation.
