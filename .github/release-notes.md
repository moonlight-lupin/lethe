**Lethe** is a fully-local, reversible document de-identifier — it replaces people and
counterparty names with stable tokens *before* you send a document to an AI, then
restores the real names in the AI's reply. Nothing ever leaves your machine.

## What's new in 1.3.0

- **Email ingestion (`.eml` / Outlook `.msg` / `.html`).** Drop an email file into
  De-identify (or Restore) and Lethe returns a de-identified **Word** document — the
  **From / To / Cc / Subject** header block is redacted along with the body, so the names
  and addresses in the headers are tokenised too. `.eml` and `.html` work out of the box;
  Outlook `.msg` is supported in the Windows installer / portable bundle (and via the
  optional `[email]` pip extra). Attachments and inline images aren't included or redacted.

## Install

| You are… | Get it | Run |
|---|---|---|
| **Windows, non-technical** | download the **`…-Setup.exe`** below and run it (per-user, no admin rights) | Start-menu / Desktop shortcut |
| **Windows, portable** | download the **`…-Portable.zip`** below, unzip, run the launcher | data stays inside the folder |
| **Windows / macOS / Linux, with Python 3.10–3.13** | `pipx install "lethe[nlp,ocr,email] @ git+https://github.com/moonlight-lupin/lethe@v1.3.0"` | `lethe` |
| **lean (no extras, smaller)** | `pipx install "git+https://github.com/moonlight-lupin/lethe@v1.3.0"` | `lethe` |

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
