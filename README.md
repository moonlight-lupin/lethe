<p align="center">
  <img src="web_static/favicon.svg" width="72" alt="Lethe logo" />
</p>

<h1 align="center">Lethe</h1>

<p align="center">
  A <b>fully-local, reversible</b> document de-identifier — it replaces people and
  counterparty names with stable tokens <i>before</i> you send a document to an AI,
  then restores the real names in the AI's reply. Nothing ever leaves your machine:
  no cloud, no API key, no internet call.
</p>

---

## Purpose

Lethe is a privacy gate for working with AI on sensitive documents. Drop in a
**Word**, **PDF**, or **Excel** file; Lethe finds the people and counterparties —
from your dictionary, pattern rules, and an optional NLP engine — replaces them
with stable placeholder tokens like `[PERSON_001]`, and hands you a de-identified
copy in the **same format** plus a **Job ID**. Paste the AI's answer back, pick the
Job ID, and Lethe swaps the real names in again. The reversal key for each job is
encrypted with a passphrase and stored only on your machine.

The names you are protecting are never transmitted anywhere — Lethe has no server
side. Named after the *Lethe*, one of the five rivers of the Greek underworld: the
river of oblivion, whose waters made souls forget.

## Key features

- **Fully local & reversible** — de-identify before the AI sees a document,
  re-identify the AI's reply afterwards. No internet, no telemetry.
- **Entity dictionary (the reliable core):** a curated list of your real people and
  counterparties with their aliases (*Acme Capital Partners* / *Acme* / *ACP*) gives
  near-100% reliability on the names that actually matter. Bulk-paste a master list.
- **NLP suggestions:** Microsoft **Presidio** + **spaCy** detect *possible* names and
  organisations not yet in your dictionary (off by default — you decide). Falls back
  to a lightweight regex name-guesser when the NLP engine isn't installed.
- **Pattern detection:** emails, phone numbers and account numbers out of the box.
- **Stable tokens:** the same name always maps to the same token — consistently
  across every file in a batch.
- **Custom token types:** beyond the built-in PERSON / COUNTERPARTY / OTHER, define your
  own categories in Settings (e.g. `PROJECT`, `FUND`) — they appear in the Type dropdowns
  and tokenise as `[PROJECT_001]`.
- **Format-preserving:** Word stays Word, Excel stays Excel (formulas preserved).
  PDFs are rebuilt as a de-identified Word file (via **pdfplumber**) — **tables become
  real Word tables**, and each source page gets a **`Page N` heading** so downstream
  tools can quote against the *original* PDF pages. The file opens with an **agent-facing
  notice header** instructing readers/AIs to cite by source page and keep the
  `[TOKEN_NNN]` placeholders verbatim.
- **Image-page warning:** Lethe flags PDF pages that are scans/figures with no
  extractable text — names rendered as pixels can't be detected (there's no OCR), so
  the gap is made visible rather than silent.
- **Encrypted vault:** each job's token→name map is sealed with your passphrase
  (PBKDF2 → Fernet). Lose the passphrase and that job is unrecoverable *by design*.
- **Review before anything is written:** Lethe shows every proposed redaction,
  highlighted in the document — nothing is changed until you confirm.
- **Multi-language detection:** download extra spaCy models (Chinese, Japanese,
  Korean, …) from the Settings tab; your dictionary works in every language regardless.
- **Themed desktop UI:** a NiceGUI app with a classical light/dark "river of oblivion"
  skin, shared with its sibling tools *Argus* and *Pythia*.
- **Ships portable:** a self-contained Windows bundle and a per-user installer — no
  admin rights required.

## Architecture

```
app.py  (NiceGUI UI — the only code at the repo root)
   │
   └─►  lethe/   (engine package — no web dependencies)
          core.py            detection + tokenisation + replace / restore
          docio.py           Word / PDF / Excel read & write
          nlp_suggester.py   Presidio + spaCy suggestions (optional)
          vault.py           encrypted, reversible token → name store
          store.py           entity dictionary (entities.json)
```

The UI is a thin layer over the `lethe` package; all detection, redaction and
storage logic lives there with no UI coupling. User data — `entities.json` and the
encrypted `vault/` — sits next to the app, never inside the package.

## How it works — the tabs

**1 · De-identify** — Upload one or more files. Lethe lists what it proposes to
redact: ✅ **known entities** (your dictionary), 🔎 **patterns** (email/phone/account),
and ⚠️ **suggestions** (NLP-detected names, off by default). Review the list, tick or
untick, set a **passphrase**, and **Generate** — you get the de-identified file(s) and
a Job ID. *When you hand the file to an AI, ask it to keep any `[TOKEN_NNN]`
placeholders exactly as written.*

**2 · Re-identify** — Paste the AI's reply (or upload it), pick the **Job ID**, enter
the same **passphrase**, and the tokens turn back into the real names. The AI's output
can be a **completely different document** from what you sent — a summary, redraft or
translation — because re-identify just maps tokens back to names; it never needs the
original file. Matching is **exact** (`[PERSON_001]`), so any token the AI altered or
dropped simply won't be restored — glance over the result and check the restored count.

**3 · Entity dictionary** — Your curated people & counterparties. This is what makes
detection dependable; generic "AI name detection" can miss names, a known list does
not. Add aliases so every variant maps to one token; bulk-import a master list.

**4 · Settings** — Download extra detection-language models on demand; define your own
**token types** (e.g. PROJECT, FUND) that appear in the Type dropdowns; toggle the
light/dark theme.

## Running it

**Double-click `Launch De-identifier.bat`** — Lethe opens in your browser at
`http://localhost:8731`. Close the black window to stop it. (First launch takes a few
seconds to start up.)

To (re)install the engine — Lethe standardises on **Python 3.13**:

```powershell
py -V:3.13 -m venv .venv313
# Full install (Presidio + spaCy suggestion engine):
.venv313\Scripts\python.exe -m pip install -r requirements.txt -r requirements-nlp.txt
# OR lean install (regex name-guesser only, smaller):
.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

The NLP engine adds the ability to *suggest* counterparties/organisations, not just
people; Lethe runs fine without it. (spaCy/Presidio have no Python 3.14 wheels yet,
which is why the project pins 3.13.) Run the checks with `python tests/test_smoke.py`
and `python tests/test_doc.py`.

## Packaging

`build_portable.ps1` produces the self-contained `dist\DeIdentifier-Portable\` folder
+ zip for teammates. Set `$WithNLP = $true` (default) for the Presidio build, or
`$false` for the lean regex-only build.

For managed deployment, `installer.iss` wraps the portable bundle into a single
per-user installer — **no admin rights**, Start-Menu/Desktop shortcuts, an
uninstaller, and silent mass-deploy:

```powershell
winget install --id JRSoftware.InnoSetup -e         # one-time
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
# -> dist\DeIdentifier-Setup.exe   (per-user; ~69 MB)
# IT silent push:  DeIdentifier-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES
```

## Limitations

- **The review step is the safety net, not the AI.** The NLP *suggestions* are a
  convenience to help you spot gaps — treat the dictionary as the source of truth and
  always eyeball the review list.
- **No OCR.** Names rendered as pixels — in a scan, a chart, a logo, a signature image —
  can't be read or redacted. Lethe **flags** image-based PDF pages so you know to check
  them, but it cannot redact text inside an image.
- **PDF page numbers:** the output's `Page N` headings refer to the *original* PDF pages
  (for citation); the Word file's own rendered pagination won't match the source.
- **Text in shapes, text boxes, embedded objects, metadata, comments and tracked
  changes is not read** — these may still carry names.
- In **Word**, a line containing a redacted name keeps its text but may lose fine
  in-line formatting (bold/italic within that line). Correct redaction is prioritised
  over formatting fidelity.
- In **Excel**, only cell *text* is edited — charts, formatting and formulas are
  preserved. Two edge cases: a redacted name that was styled with mixed formatting
  *within a single cell* loses that cell's in-line formatting (the redaction itself is
  still correct), and a name buried in a *formula string literal* (e.g.
  `="Acme " & A1`) isn't caught — rare for de-identification.
- **The passphrase cannot be recovered.** Lose it and the re-identification mapping for
  that job is gone. Keep the Job ID with the document.

## License & credits

Lethe is released under the **[GNU Affero General Public License v3.0 or later](LICENSE)**
(AGPL-3.0-or-later). If you run a modified version as a network service, the AGPL
requires you to offer its users the corresponding source. See [NOTICE](NOTICE) for
third-party components and [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute
(AGPL + DCO sign-off).

It builds on Microsoft **[Presidio](https://github.com/microsoft/presidio)** and
**[spaCy](https://spacy.io)** (both MIT-licensed) for name detection. Lethe is not
affiliated with or endorsed by Microsoft or the spaCy project.
