**Lethe** is a fully-local, reversible document de-identifier — it replaces people and
counterparty names with stable tokens *before* you send a document to an AI, then
restores the real names in the AI's reply. Nothing ever leaves your machine.

## What's new in 1.2.0

- **New "Restore" tab — re-identify documents tokenised *outside* Lethe.** When the
  de-identification was done by another tool, a colleague, or by hand (so there's no Job
  ID to reverse), drop the file in: Lethe scans it for `[bracketed]` tokens, lets you type
  the real name behind each, and rebuilds the document in the same format. Each token gets
  an explicit **Type** dropdown and a **Save** checkbox, so *you* decide what's an entity
  and how it's filed in your dictionary — no guessing. It also doubles as a quick template
  filler for forms with `[CLIENT]` / `[DATE]` / `[AMOUNT]` placeholders.
- **Settings → Files & folders.** See exactly where Lethe keeps your data (the entity
  dictionary, custom token types and the encrypted vault) and where it runs from — each
  with an **Open** button that reveals the folder in your file manager. Handy for backups.

## Install

| You are… | Get it | Run |
|---|---|---|
| **Windows, non-technical** | download the **`…-Setup.exe`** below and run it (per-user, no admin rights) | Start-menu / Desktop shortcut |
| **Windows, portable** | download the **`…-Portable.zip`** below, unzip, run the launcher | data stays inside the folder |
| **Windows / macOS / Linux, with Python 3.10–3.13** | `pipx install "lethe[nlp,ocr] @ git+https://github.com/moonlight-lupin/lethe@v1.2.0"` | `lethe` |
| **lean (no NLP, smaller)** | `pipx install "git+https://github.com/moonlight-lupin/lethe@v1.2.0"` | `lethe` |

The Windows installer and portable bundle embed their own Python — **no Python needed**
on the target PC. The `pipx` route is the cross-platform way for macOS and Linux; the
`[nlp]` extra adds the Presidio + spaCy suggestion engine and `[ocr]` adds scanned-page
OCR (otherwise Lethe falls back to a regex name-guesser and flags scanned pages). Either
way, Lethe opens at `http://localhost:8731`.

## Highlights

- Word / PowerPoint / PDF / Excel in, de-identified copies out (same format; PDFs → a
  de-identified Word file with `Page N` anchors and an agent-facing notice header).
- A curated **entity dictionary** is the reliable core; optional NLP **suggestions** and
  pattern detection (emails / phones / accounts) on top.
- **Reversible**: each job's token→name map is encrypted with your passphrase; restore
  the real names into the AI's reply afterwards.
- Custom token types, a spreadsheet table preview, scanned-page OCR with review prompts,
  and a classical light/dark theme.

Released under the **Apache License 2.0**. See the README for full documentation.
