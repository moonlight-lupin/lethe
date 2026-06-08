# Document De-identifier

A small, **fully local** tool that strips people and counterparties out of
documents *before* you send them to an AI model — and lets you put the real
names back into the AI's answer afterwards.

Nothing leaves your machine. There is no cloud service, no API key, no internet
call. The names you are trying to protect are never transmitted anywhere.

---

## How to start it

**Double-click `Launch De-identifier.bat`.**

A black window opens and your browser shows the app at `http://localhost:8731`.
To stop it, close the black window.

(First launch takes a few seconds while it starts up.)

---

## How it works — the three tabs

### 1 · De-identify
1. Upload a **Word (.docx)**, **PDF**, or **Excel (.xlsx)** file.
2. The tool lists everything it proposes to redact:
   - ✅ **Known entities** — names from your dictionary (tab 3). These are the
     reliable ones.
   - 🔎 **Patterns** — emails, phone numbers, account numbers.
   - ⚠️ **Possible names / counterparties** — people and organisations detected
     by the NLP engine (Microsoft Presidio + spaCy) that aren't in your
     dictionary yet. **Off by default** — you decide. (If the NLP engine isn't
     installed, this falls back to a lighter regex name-guesser, people only.)
3. **Review the list.** Untick anything that should stay; tick any suggested
   name you want gone. *Nothing is written until you confirm.*
4. Enter a **passphrase** and click **Generate**. You get:
   - the de-identified document (same format — Word stays Word, Excel stays
     Excel; PDFs come back as a de-identified Word file), and
   - a **Job ID**.

Real names are replaced with stable tokens like `[PERSON_001]`,
`[COUNTERPARTY_001]`, `[EMAIL_001]`. The same name always gets the same token.

### 2 · Re-identify
Paste the AI's reply (or upload it), pick the **Job ID**, enter the same
**passphrase**, and the tokens turn back into the real names.

### 3 · Entity dictionary
**This is the most important part.** A curated list of your real people and
counterparties (with their aliases — e.g. *Acme Capital Partners* / *Acme* /
*ACP*) gives near-100% reliability on the names that actually matter. Generic
"AI name detection" can miss names; a known list does not. Maintain this list
and the tool is genuinely dependable.

You can bulk-paste your counterparty master list under **Bulk import**.

---

## Important to understand (limitations)

- **The review step is the safety net, not the AI.** The automatic name
  *suggestions* are a convenience to help you spot gaps. Treat the dictionary as
  the source of truth and always eyeball the review list.
- **PDFs** are converted to text/Word output (PDFs can't be safely edited in
  place). The text is what you feed an AI anyway, so this is by design.
- **Scanned/image PDFs** won't work — there's no OCR. Only PDFs with real text.
- In **Word**, a line that contains a redacted name keeps its text but may lose
  fine in-line formatting (bold/italic within that one line). Correct redaction
  is prioritised over formatting fidelity.
- **The passphrase cannot be recovered.** Lose it and the re-identification
  mapping for that job is gone. Keep the Job ID with the document.
- The encrypted mappings live in the `vault\` folder next to the app.

---

## If you ever need to reinstall the engine

The project standardises on **Python 3.13**. Open PowerShell in this folder:

```powershell
py -V:3.13 -m venv .venv313
# Full install (with the Presidio + spaCy suggestion engine):
.venv313\Scripts\python.exe -m pip install -r requirements.txt -r requirements-nlp.txt
# OR lean install (regex name-guesser only, smaller):
.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

The NLP engine (Presidio + spaCy) adds the ability to *suggest*
counterparties/organisations, not just people. The app runs fine without it — it
falls back to the regex name-guesser. (spaCy/Presidio have no Python 3.14 wheels
yet, which is why the project pins 3.13.)

## Rebuilding the portable distribution

`build_portable.ps1` produces the self-contained `dist\DeIdentifier-Portable\`
folder + zip for teammates. Set `$WithNLP = $true` (default) for the Presidio
build on Python 3.13, or `$false` for the lean regex-only build.

## Optional: building the installer (`DeIdentifier-Setup.exe`)

For managed deployment (recommended once IT whitelists the app), `installer.iss`
wraps the portable bundle into a single per-user installer — **no admin rights**,
Start-Menu/Desktop shortcuts, an uninstaller, and silent mass-deploy for IT.

```powershell
# one-time: install the Inno Setup compiler
winget install --id JRSoftware.InnoSetup -e
# build (after build_portable.ps1 has created dist\DeIdentifier-Portable\)
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
# -> dist\DeIdentifier-Setup.exe  (per-user install; ~69 MB)
```

IT can push it silently:  `DeIdentifier-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES`

---

## Files

| File | What it is |
|------|------------|
| `Launch De-identifier.bat` | Double-click to start |
| `app.py` | The user interface |
| `core.py` | Detection + redaction logic |
| `docio.py` | Reading/writing Word, PDF, Excel |
| `vault.py` | Encrypted, reversible mapping store |
| `store.py` | Your entity dictionary |
| `entities.json` | Your saved people/counterparties (created on first save) |
| `vault\` | Encrypted re-identification mappings |
