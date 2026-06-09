**Lethe** is a fully-local, reversible document de-identifier — it replaces people and
counterparty names with stable tokens *before* you send a document to an AI, then
restores the real names in the AI's reply. Nothing ever leaves your machine.

## Install

| You are… | Get it | Run |
|---|---|---|
| **Windows, non-technical** | download **`Lethe-1.0.0-Setup.exe`** below and run it (per-user, no admin rights) | Start-menu / Desktop shortcut |
| **Windows, portable** | download **`Lethe-1.0.0-Portable.zip`**, unzip, run the launcher | data stays inside the folder |
| **Windows / macOS / Linux, with Python 3.10–3.13** | `pipx install "lethe[nlp] @ git+https://github.com/moonlight-lupin/lethe@v1.0.0"` | `lethe` |
| **lean (no NLP, smaller)** | `pipx install "git+https://github.com/moonlight-lupin/lethe@v1.0.0"` | `lethe` |

The Windows installer and portable bundle embed their own Python — **no Python needed**
on the target PC. The `pipx` route is the cross-platform way for macOS and Linux; the
`[nlp]` extra adds the Presidio + spaCy suggestion engine (otherwise Lethe falls back to
a built-in regex name-guesser). Either way, Lethe opens at `http://localhost:8731`.

## Highlights

- Word / PDF / Excel in, de-identified copies out (same format; PDFs → a de-identified
  Word file with `Page N` anchors and an agent-facing notice header).
- A curated **entity dictionary** is the reliable core; optional NLP **suggestions** and
  pattern detection (emails / phones / accounts) on top.
- **Reversible**: each job's token→name map is encrypted with your passphrase; restore
  the real names into the AI's reply afterwards.
- Custom token types, a spreadsheet table preview, image-based-PDF-page warnings, and a
  classical light/dark theme.

Released under the **Apache License 2.0**. See the README for full documentation.
