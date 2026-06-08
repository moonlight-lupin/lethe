r"""
Document De-identifier -- a local, reversible PII de-identification gate.

NiceGUI desktop UI. Everything runs on this machine; nothing is sent anywhere.
The engine lives in core / docio / vault / store / nlp_suggester -- this file is
purely the interface.

Run:  .venv313\Scripts\python.exe app.py   (or use the launcher)
"""
from __future__ import annotations

import os
import sys

# Run correctly no matter the working directory (launcher / double-click).
_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import html as _html
import io
import secrets
import urllib.parse
import zipfile
from datetime import datetime, timezone

from nicegui import app, run, ui

from lethe import (
    Entity,
    _whole_word_regex,
    assign_tokens,
    build_replacer,
    build_restorer,
    detect,
    extract_text,
    file_kind,
    load_entities,
    merge_entities,
    nlp_suggester,
    pdf_warnings,
    redact_document,
    save_entities,
    vault,
)

# ---- look & feel — "Lethe · the river of oblivion" theme --------------------
# A classical reskin in the same family as Argus ("The Watcher's Codex") and
# Pythia ("Oracle's Manuscript"): warm parchment neutrals, a Cinzel inscription
# wordmark, bronze-gold ornament and a Greek-key meander — with Lethe's own
# dusk-amethyst accent (sleep, poppies, forgetting). The same design tokens
# invert under dark mode (`body.body--dark`, toggled from the header) with no
# markup changes — exactly the token architecture the two sibling apps use.
PRIMARY = "#6a4690"  # dusk amethyst — Lethe's accent within the family
APP_VERSION = "1.0.0"
REPO_URL = "https://github.com/moonlight-lupin/lethe"

ui.colors(primary=PRIMARY, secondary="#4a3066", accent="#7d56a6",
          positive="#3f7d4e", negative="#a83a2c", warning="#9b6f16", dark="#14110b")

# Review-table badge colours, kept in the amethyst/gold family.
TYPE_COLOR = {"PERSON": "deep-purple-6", "COUNTERPARTY": "amber-8", "OTHER": "pink-7",
              "EMAIL": "blue-grey-6", "PHONE": "blue-grey-6", "ACCOUNT": "blue-grey-6"}
SOURCE_BADGE = {"dictionary": ("Known entity", "deep-purple-6"),
                "pattern": ("Pattern", "blue-grey-6"),
                "suggestion": ("Suggested", "amber-8"),
                "manual": ("Manual", "pink-7")}


def _svg_uri(svg: str) -> str:
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


def _river_mark(gold: str, amethyst: str) -> str:
    """Lethe's emblem — three flowing currents, a dusk-amethyst middle stream."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
        f'<path d="M2 7.5 q3 -3 6 0 t6 0 t6 0" fill="none" stroke="{gold}" stroke-width="1.9" stroke-linecap="round"/>'
        f'<path d="M2 12.5 q3 -3 6 0 t6 0 t6 0" fill="none" stroke="{amethyst}" stroke-width="1.9" stroke-linecap="round"/>'
        f'<path d="M2 17.5 q3 -3 6 0 t6 0 t6 0" fill="none" stroke="{gold}" stroke-width="1.9" stroke-linecap="round"/>'
        '</svg>')


def _meander(stroke: str) -> str:
    """A Greek-key meander tile — the family's restrained classical divider."""
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='20' height='13'>"
            f"<path d='M2 11 V2 H15 V11 H6 V5.5 H11 V8.5' fill='none' stroke='{stroke}' stroke-width='1.2'/></svg>")


_MARK_LIGHT = _svg_uri(_river_mark("#9a6a1d", "#6a4690"))
_MARK_DARK = _svg_uri(_river_mark("#d8a945", "#b79be0"))
_MEANDER_LIGHT = _svg_uri(_meander("#9a6a1d"))
_MEANDER_DARK = _svg_uri(_meander("#d8a945"))

THEME_CSS = """
<style>
/* Cinzel — Roman-inscription capitals, self-hosted (OFL) so the app stays
   fully offline. Used only for the wordmark. */
@font-face{font-family:"Cinzel";font-style:normal;font-weight:400 700;font-display:swap;
  src:url("/static/fonts/cinzel-latin.woff2") format("woff2");}

:root{
  /* Neutrals — warm parchment / stone (shared with Argus + Pythia) */
  --bg:#efe6d4; --panel:#fdfbf6; --panel2:#f4ecda; --border:#e3d9c2;
  --text:#3a332a; --muted:#877a61; --chip:#ece2cd;
  /* Accent — dusk amethyst (Lethe's own hue in the family) */
  --accent:#6a4690; --accent-ink:#fdfbf6; --accent2:#7d56a6;
  /* Ornament — bronze / antique gold */
  --gold:#9a6a1d; --gold-2:#c4953f;
  --danger:#a83a2c; --warn:#9b6f16; --ok:#3f7d4e;
  /* Warm-tinted elevation (shadows on parchment read brown, not grey) */
  --e1:0 1px 2px rgba(58,42,16,.06),0 1px 3px rgba(58,42,16,.05);
  --e2:0 2px 8px -2px rgba(58,42,16,.12),0 2px 5px -3px rgba(58,42,16,.08);
  --e3:0 14px 34px -10px rgba(58,42,16,.26),0 8px 14px -10px rgba(58,42,16,.16);
  --r:12px; --r-sm:8px;
  --font-display:"Cinzel","Trajan Pro",Georgia,serif;
  --font-serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,Cambria,serif;
}
/* Dark "still water" mode — obsidian ground, glowing amethyst + gold */
body.body--dark{
  --bg:#14110b; --panel:#1f1810; --panel2:#2a2216; --border:#3a2f1e;
  --text:#e8dec7; --muted:#a4967b; --chip:#2a2216;
  --accent:#b79be0; --accent-ink:#1c1330; --accent2:#cdb6f0;
  --gold:#d8a945; --gold-2:#f0cd80;
  --danger:#f0a0a0; --warn:#f0c869; --ok:#7fcfa6;
  --e1:0 1px 2px rgba(0,0,0,.4); --e2:0 2px 10px -2px rgba(0,0,0,.5); --e3:0 16px 40px -10px rgba(0,0,0,.65);
}

html,body{background:var(--bg)!important;}
body{color:var(--text);min-height:100vh;
  transition:background-color .25s cubic-bezier(.2,.8,.2,1),color .25s cubic-bezier(.2,.8,.2,1);}
.nicegui-content,.q-page,.q-tab-panel,.q-tab-panels{background:transparent!important;}

/* tailwind neutrals used in markup, remapped onto the palette */
.text-slate-500,.text-slate-400,.text-gray-500,.text-gray-400{color:var(--muted)!important;}
.text-teal-700{color:var(--accent2)!important;}
.text-amber-700{color:var(--warn)!important;}
.bg-gray-100,.bg-gray-200{background:var(--chip)!important;}

/* ── header / wordmark ─────────────────────────────────────────────── */
.q-header{background:var(--panel)!important;color:var(--text)!important;
  border-bottom:1px solid var(--border);box-shadow:var(--e1);}
/* Header accent elements (Guide, chip, theme toggle) also default to Quasar's
   fixed `primary`; pin them to --accent too so they brighten in dark mode in
   lockstep with the active tab — one uniform amethyst across the whole accent. */
.q-header .q-btn,.q-header .q-btn__content,.q-header .q-chip.q-chip,.q-header .q-chip__content,.q-header .q-chip .q-icon{color:var(--accent)!important;}
.wordmark{font-family:var(--font-display);font-weight:700;letter-spacing:.18em;font-size:21px;
  text-transform:uppercase;line-height:1.05;
  background:linear-gradient(180deg,var(--gold-2) 0%,var(--gold) 64%,#6f4c14 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;}
body.body--dark .wordmark{background:linear-gradient(180deg,#f0d488 0%,var(--gold) 70%,#a4842f 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;}
.wordmark-sub{color:var(--muted);font-size:11px;letter-spacing:.02em;}
.lethe-mark{height:26px;width:28px;background-repeat:no-repeat;background-position:center;
  background-size:contain;background-image:url("__MARK_LIGHT__");}
body.body--dark .lethe-mark{background-image:url("__MARK_DARK__");}

/* ── Greek-key meander divider ─────────────────────────────────────── */
.meander{height:13px;background-repeat:repeat-x;background-position:center;opacity:.5;
  background-image:url("__MEANDER_LIGHT__");}
body.body--dark .meander{opacity:.45;background-image:url("__MEANDER_DARK__");}

/* ── cards / panels ────────────────────────────────────────────────── */
.q-card{background:var(--panel)!important;color:var(--text)!important;
  border:1px solid var(--border)!important;border-radius:var(--r)!important;box-shadow:var(--e1)!important;}
.q-card .text-base.font-medium,.q-card .text-lg{font-family:var(--font-serif);font-weight:600;
  color:var(--text)!important;letter-spacing:.01em;}

/* ── inputs ────────────────────────────────────────────────────────── */
.q-field--outlined .q-field__control{background:var(--panel2)!important;border-radius:var(--r-sm)!important;}
.q-field--outlined .q-field__control:before{border-color:var(--border)!important;}
.q-field--outlined .q-field__control:hover:before{border-color:var(--accent)!important;}
.q-field--outlined.q-field--focused .q-field__control:after{border-color:var(--accent)!important;}
.q-field__native,.q-field__input,.q-field__native textarea,textarea.q-field__native{color:var(--text)!important;}
.q-field__label,.q-field__marginal,.q-field__messages{color:var(--muted)!important;}

/* ── popup menus / dropdowns ───────────────────────────────────────── */
.q-menu{background:var(--panel)!important;color:var(--text)!important;border:1px solid var(--border);
  border-radius:var(--r-sm)!important;box-shadow:var(--e3)!important;}
.q-menu .q-item,.q-menu .q-item__label{color:var(--text)!important;}
.q-menu .q-item:hover{background:var(--chip)!important;}

/* ── tables ────────────────────────────────────────────────────────── */
.q-table__card,.q-table{background:transparent!important;color:var(--text)!important;box-shadow:none!important;}
.q-table thead th{color:var(--muted)!important;font-weight:700;text-transform:uppercase;
  font-size:11px;letter-spacing:.05em;border-bottom:1px solid var(--border)!important;}
.q-table tbody td{border-bottom:1px solid var(--border)!important;color:var(--text)!important;}
.q-table tbody tr:hover{background:var(--chip)!important;}

/* ── tabs ──────────────────────────────────────────────────────────── */
.q-tabs{color:var(--muted)!important;border-bottom:1px solid var(--border);}
.q-tab{color:var(--muted)!important;}
/* Quasar pins active-color/indicator to its fixed `primary`, which never flips
   for dark mode. Drive both from the mode-aware --accent (bright amethyst in
   dark, deep amethyst in light) with enough specificity to beat Quasar's
   `.text-primary !important`, so the active tab reads as light as the header. */
.q-tabs .q-tab--active,.q-tabs .q-tab--active .q-tab__label{color:var(--accent)!important;}
.q-tabs .q-tab__indicator{background-color:var(--accent)!important;}
.q-tab__label{font-weight:600;}

/* ── chips / uploader / expansion ──────────────────────────────────── */
.q-chip{background:var(--chip)!important;color:var(--muted)!important;border-radius:999px;}
.q-btn{border-radius:var(--r-sm)!important;}
.q-uploader{background:var(--panel2)!important;border:1px dashed var(--border)!important;
  border-radius:var(--r-sm)!important;color:var(--text)!important;box-shadow:none!important;}
.q-uploader__header{background:var(--accent)!important;color:var(--accent-ink)!important;}
.q-expansion-item .q-item{border-radius:var(--r-sm);}

/* ── document preview ──────────────────────────────────────────────── */
.doc-preview{white-space:pre-wrap;word-break:break-word;font-size:13.5px;line-height:1.75;
  max-height:62vh;overflow:auto;background:var(--panel)!important;border:1px solid var(--border);
  border-radius:var(--r);padding:16px 18px;color:var(--text);font-family:var(--font-serif);}
.pdf-warn{background:color-mix(in srgb,var(--warn) 14%,var(--panel));
  border:1px solid color-mix(in srgb,var(--warn) 45%,transparent);color:var(--warn);
  border-radius:var(--r-sm);padding:9px 13px;margin-bottom:10px;font-size:12.5px;line-height:1.5;}
.pdf-warn b{color:var(--warn);}
mark.hl{border-radius:3px;padding:0 1px;color:inherit;}
mark.hl-PERSON{background:#e7dcf2;}
mark.hl-COUNTERPARTY{background:#f0e2c4;}
mark.hl-OTHER{background:#f3dcdf;}
mark.hl-EMAIL,mark.hl-PHONE,mark.hl-ACCOUNT{background:#e6ddc9;}
mark.hl.active{outline:2px solid var(--accent);background:#f7e7a8;}
body.body--dark mark.hl{color:#1c1408;}
body.body--dark mark.hl-PERSON{background:#b79be0;}
body.body--dark mark.hl-COUNTERPARTY{background:#d8a945;}
body.body--dark mark.hl-OTHER{background:#e0a3ad;}
body.body--dark mark.hl-EMAIL,body.body--dark mark.hl-PHONE,body.body--dark mark.hl-ACCOUNT{background:#b6a886;}
body.body--dark mark.hl.active{outline:2px solid var(--accent);background:#f0cd80;}
::selection{background:#e7dcf2;}
body.body--dark ::selection{background:#5a467e;color:#fdfbf6;}

/* ── guide markdown ────────────────────────────────────────────────── */
.guide-md{font-size:.9rem;line-height:1.6;color:var(--text);}
.guide-md h1,.guide-md h2,.guide-md h3{font-family:var(--font-serif);font-weight:600;
  color:var(--accent2);margin:.9rem 0 .25rem;}
.guide-md h1{font-size:1.15rem}.guide-md h2{font-size:1.05rem}.guide-md h3{font-size:1rem}
.guide-md p{margin:.35rem 0}.guide-md ul{margin:.2rem 0 .2rem 1.1rem;list-style:disc}
.guide-md li{margin:.12rem 0}
.guide-md code{background:var(--panel2);padding:0 3px;border-radius:3px;font-size:.85em}

/* ── About section (mirrors Pythia's AboutPage; two columns fill the card) ── */
.about{font-size:13.5px;line-height:1.6;color:var(--text);}
.about p{margin:.5rem 0;}
.about a{color:var(--accent2);text-decoration:none;}
.about a:hover{text-decoration:underline;}
.about h4{font-family:var(--font-serif);font-weight:600;color:var(--text);
  margin:1rem 0 .25rem;font-size:14px;}
.about ul{margin:.3rem 0 .3rem 1.2rem;list-style:disc;}
.about li{margin:.2rem 0;}
.about code{background:var(--panel2);padding:0 4px;border-radius:3px;font-size:.85em;}
.about .meta{display:flex;align-items:center;gap:12px;margin:.2rem 0 .6rem;}
.about .pill{background:var(--chip);color:var(--muted);border-radius:999px;
  padding:2px 10px;font-size:11px;font-weight:600;}
.about .gh{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);
  border-radius:var(--r-sm);padding:4px 10px;font-size:12px;font-weight:600;color:var(--text);}
.about .gh:hover{border-color:var(--accent);text-decoration:none;}
.about .gh svg{width:18px;height:18px;}
.about-grid{display:grid;grid-template-columns:1fr 1fr;gap:2px 44px;align-items:start;}
.about-col>:first-child{margin-top:0;}
@media(max-width:860px){.about-grid{grid-template-columns:1fr;}}
.about .stack{color:var(--muted);font-size:11.5px;margin-top:1rem;
  padding-top:.6rem;border-top:1px solid var(--border);}
</style>
""".replace("__MARK_LIGHT__", _MARK_LIGHT).replace("__MARK_DARK__", _MARK_DARK) \
   .replace("__MEANDER_LIGHT__", _MEANDER_LIGHT).replace("__MEANDER_DARK__", _MEANDER_DARK)

GUIDE_MD = """
### What this tool does
Replaces real people & counterparty names with placeholder tokens (like
`[PERSON_001]`, `[COUNTERPARTY_001]`) **before** you send a document to an AI —
then puts the real names back into the AI's reply. Everything runs on this
computer; nothing is ever sent anywhere.

### 1 · De-identify
1. Drag in one or more **Word / PDF / Excel** files (or click *Try a sample memo*).
2. The right pane shows the document with detected names **highlighted**
   (amethyst = person, gold = counterparty, grey = email/phone/account).
3. In the **Review** list:
   - **Tick** what to remove. (Suggestions are off by default.)
   - **Click a row** to jump to it in the document.
   - Fix a wrong **Type** using its dropdown.
   - Missed something? **Select the text** in the document, then **Redact selection**.
   - Edited your dictionary? Press **↻** to re-scan.
4. Optionally set a **passphrase**, then **Generate**. You get the de-identified
   file(s), a **reference** list of tokens, and a **Job ID**.

**When you hand the file to an AI**, add an instruction like *"Keep any
`[TOKEN_NNN]` placeholders exactly as written."* The AI can rewrite, summarise or
translate the document however you like — it just needs to leave the tokens intact
so the real names can go back afterwards.

### 2 · Re-identify
The AI's reply can be a **completely different document** from the one you sent —
a summary, a redraft, a translation, a table. Re-identify simply swaps every token
it finds back to the real name, so it works on whatever text you give it; it never
needs the original file.

1. Pick the conversion from **Past conversions**.
2. Enter the passphrase (if you set one).
3. **Upload the AI's reply file** (same format back) *or* paste its text.
4. Click **Re-identify** — the real names are restored, and the count shows how
   many tokens were swapped back.

Restoration matches tokens **exactly** (`[PERSON_001]`). If the AI changed a token —
dropped the brackets, changed its case, or split it across a line — that one name
won't be restored, so glance over the result and check the count looks right.

### 3 · Entity dictionary
Your curated list of people & counterparties — this is what makes detection
reliable. Add **aliases** (short / legal / trading names) so every variant maps
to the same token. Newly-found names you redact are added here automatically.

### What's saved on this computer
Everything stays in the app's own folder — nothing is uploaded:
- **Entity dictionary** (`entities.json`) — your people & counterparties, in plain text.
- **Reversal keys** (`vault` folder) — one **encrypted** file per job, holding the
  token → real-name mapping, locked by the passphrase you set (blank = unprotected).
  This is the *only* way to re-identify a job; delete it or lose the passphrase and
  that job can no longer be reversed.
- **History index** (`vault\\index.json`) — the *Past conversions* list (date, file
  name, redaction count) in plain text. It does **not** contain the real names.

### What it can't remove
The tool reads the **text** of your files. It does **not** touch:
- **Images & logos** — a counterparty logo, a signature image, a scanned stamp, or any
  name *inside a picture* is not detected (there is no image reading / OCR).
- **Scanned / image-only PDFs** — no selectable text, so nothing is found. Lethe
  **flags** image-based pages so you know to check them, but it can't read them (no OCR).
- Text in **shapes, text boxes, charts or embedded objects**, and document
  **metadata, comments or tracked changes** — these may still carry names.
- Amounts, dates and ID numbers — unless they match the email / phone / account patterns.

Always glance over the document preview before sending — your dictionary and your
review are the real safeguard.

### Good to know
- **Keep your passphrase + Job ID together** — you need both to reverse a job.
- A **blank passphrase** means the reversal key is saved unprotected.
- **PDFs** come back as Word — tables stay tables, and each page gets a *Page N*
  heading (matching the original PDF) so you can cite pages. The file opens with a short
  notice telling an AI to cite by source page and keep the tokens intact. Image/scan
  pages are flagged.
- Nothing leaves this machine — no internet, no cloud.
"""

# GitHub "Octocat" mark (same glyph Pythia's AboutPage uses).
_GH_SVG = ('<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 '
           '3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53'
           '-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 '
           '1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15'
           '-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53'
           '-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 '
           '3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0'
           '-4.42-3.58-8-8-8Z"/></svg>')

# About card — mirrors Pythia's AboutPage layout (version pill + GitHub link,
# intro, mythology note, engine bullets, license, tech-stack line).
ABOUT_HTML = f"""
<div class="about">
  <div class="meta">
    <span class="pill">v{APP_VERSION}</span>
    <a class="gh" href="{REPO_URL}" target="_blank" rel="noreferrer">{_GH_SVG} View on GitHub</a>
  </div>
  <div class="about-grid">
    <div class="about-col">
      <p><b>Lethe</b> is a fully-local, reversible document de-identifier. It replaces real
      people and counterparty names with stable tokens (like <code>[PERSON_001]</code>)
      <b>before</b> you send a document to an AI, then restores the real names in the AI's
      reply. Everything runs on this machine — no cloud, no API key, no internet call.</p>
      <p>It is named after the <i>Lethe</i>, one of the five rivers of the Greek underworld —
      the river of oblivion, whose waters erased the memories of those who drank from them.</p>
      <h4>Detection engine</h4>
      <ul>
        <li>Microsoft <a href="https://github.com/microsoft/presidio" target="_blank" rel="noreferrer">Presidio</a>
          (analyzer + anonymizer) — the PII detection framework</li>
        <li><a href="https://spacy.io" target="_blank" rel="noreferrer">spaCy</a> with the
          <code>en_core_web_sm</code> model — named-entity recognition for people &amp; organisations</li>
        <li>Falls back to a built-in regex name-guesser when the NLP engine isn't installed —
          your entity dictionary works either way</li>
      </ul>
    </div>
    <div class="about-col">
      <h4>Privacy &amp; storage</h4>
      <p>Your entity dictionary (<code>entities.json</code>) and the encrypted, reversible
      mappings (the <code>vault</code> folder) never leave this folder. Each job's reversal key
      is encrypted with your passphrase; lose the passphrase and that job can no longer be reversed.</p>
      <h4>License</h4>
      <p>Lethe is released under the
      <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank" rel="noreferrer">GNU Affero
      General Public License v3.0</a>. Its detection libraries (Presidio, spaCy and the
      <code>en_core_web_sm</code> model) are MIT-licensed; Lethe is not affiliated with or endorsed
      by Microsoft or the spaCy project.</p>
    </div>
  </div>
  <p class="stack">Built with NiceGUI · Microsoft Presidio · spaCy · python-docx · openpyxl · pypdf · cryptography.</p>
</div>
"""

SAMPLE = (
    "Dear Mr John Smith,\n\n"
    "Acme Capital Partners (\"Acme\") confirms the secondary transaction with "
    "Meridian Holdings Pte Ltd. The mandate was led by Priya Raman and "
    "counter-signed by Wibowo Santoso of Garuda Ventures.\n\n"
    "Please remit to the DBS Bank account. Queries: john.smith@acme.com or "
    "+65 6789 1234. Reference account 1234-5678-9012.\n\n"
    "Kind regards,\nJane Doe"
)


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def _reference_text(job_id: str, created: str, sources: list[str], token_to_real: dict) -> bytes:
    lines = ["DE-IDENTIFICATION REFERENCE",
             f"Job ID : {job_id}",
             f"Created: {created.replace('T', ' ')[:19]} UTC",
             f"Sources: {', '.join(sources)}", "",
             f"{'TOKEN':24}REAL VALUE", f"{'-' * 24}{'-' * 30}"]
    for t, v in token_to_real.items():
        lines.append(f"{t:24}{v}")
    lines += ["", "Keep this file secure — it reverses the de-identification."]
    return "\n".join(lines).encode("utf-8")


def _preview_html(text: str, items: list) -> str:
    """Render the document text with every detected item wrapped in a <mark>
    (data-iid = item index) so the client can highlight on demand."""
    spans = []
    for i, it in enumerate(items):
        for s in it.surfaces:
            for m in _whole_word_regex(s).finditer(text):
                spans.append((m.start(), m.end(), i, it.type))
    spans.sort(key=lambda x: x[1] - x[0], reverse=True)  # longest wins
    taken, acc = [], []
    for sp in spans:
        if any(sp[0] < e and s < sp[1] for s, e, _, _ in taken):
            continue
        acc.append(sp)
        taken.append(sp)
    acc.sort(key=lambda x: x[0])
    out, pos = [], 0
    for s, e, i, t in acc:
        out.append(_html.escape(text[pos:s]))
        out.append(f'<mark class="hl hl-{t}" data-iid="{i}">{_html.escape(text[s:e])}</mark>')
        pos = e
    out.append(_html.escape(text[pos:]))
    return '<div class="doc-preview">' + "".join(out) + "</div>"


def _guide_dialog():
    with ui.dialog() as dlg, ui.card().classes("max-w-2xl").style("max-height:85vh;overflow:auto"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("How to use this tool").classes("text-lg font-semibold").style(f"color:{PRIMARY}")
            ui.button(icon="close", on_click=dlg.close).props("flat round dense")
        ui.markdown(GUIDE_MD).classes("guide-md")
        ui.button("Got it", on_click=dlg.close).props("unelevated no-caps").classes("self-end")
    return dlg


def main():
    app.add_static_files("/static", os.path.join(_HERE, "web_static"))
    ui.add_head_html(THEME_CSS)
    # remember the last text selection inside the preview, even after a click
    ui.add_body_html("<script>document.addEventListener('mouseup',function(){"
                     "try{var s=window.getSelection().toString();"
                     "if(s&&s.trim())window.__deidSel=s;}catch(e){}});</script>")

    guide = _guide_dialog()
    dark = ui.dark_mode(value=False)

    with ui.header(elevated=False).classes("items-center justify-between px-6 py-2"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.html('<div class="lethe-mark"></div>')
            with ui.column().classes("gap-0"):
                ui.html('<span class="wordmark">Lethe</span>')
                ui.html('<span class="wordmark-sub">Document de-identifier · the river of oblivion</span>')
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.button("Guide", icon="help_outline", on_click=guide.open).props("flat no-caps")
            ui.chip("Local · offline", icon="lock").props("outline")
            theme_btn = ui.button(icon="dark_mode").props("flat round dense").tooltip("Toggle light / dark")

            def _toggle_theme():
                dark.toggle()
                theme_btn.props(f'icon={"light_mode" if dark.value else "dark_mode"}')

            theme_btn.on("click", _toggle_theme)

    ui.html('<div class="meander w-full"></div>')

    with ui.tabs().classes("w-full max-w-6xl mx-auto").props(
            "align=left active-color=primary indicator-color=primary no-caps") as tabs:
        t_deid = ui.tab("De-identify", icon="lock")
        t_reid = ui.tab("Re-identify", icon="lock_open")
        t_dict = ui.tab("Entity dictionary", icon="menu_book")
        t_set = ui.tab("Settings", icon="settings")

    with ui.tab_panels(tabs, value=t_deid).classes("w-full max-w-6xl mx-auto bg-transparent"):
        with ui.tab_panel(t_deid).classes("p-0"):
            build_deidentify_panel()
        with ui.tab_panel(t_reid).classes("p-0"):
            build_reidentify_panel()
        with ui.tab_panel(t_dict).classes("p-0"):
            build_dictionary_panel()
        with ui.tab_panel(t_set).classes("p-0"):
            build_settings_panel()


# ============================================================================
# 1 · DE-IDENTIFY
# ============================================================================
def build_deidentify_panel():
    files: list[dict] = []          # [{name, kind, data}]
    manual_entities: list[Entity] = []
    state: dict = {"items": [], "preview_idx": 0}

    with ui.column().classes("w-full gap-5 pt-5"):
        # ---- add documents ----
        with ui.card().classes("w-full rounded-xl shadow-sm"):
            ui.label("Add documents").classes("text-base font-medium")
            ui.label("Word, PDF or Excel — one or many. Same name → same token across all of them.").classes(
                "text-sm text-slate-500")
            with ui.row().classes("items-center gap-4 mt-2 w-full"):
                ui.upload(label="Drop / browse files", multiple=True, auto_upload=True,
                          on_upload=lambda e: on_file(e)).props(
                    'accept=".docx,.pdf,.xlsx,.txt" flat bordered').classes("flex-1")
                ui.button("Try a sample memo", icon="description",
                          on_click=lambda: on_sample()).props("outline no-caps")
            files_row = ui.row().classes("gap-2 flex-wrap mt-1")

            @ui.refreshable
            def render_files():
                files_row.clear()
                with files_row:
                    for i, f in enumerate(files):
                        with ui.row().classes("items-center gap-1 bg-gray-100 rounded-lg px-2 py-1"):
                            ui.icon("description", size="16px").classes("text-slate-500")
                            ui.label(f["name"]).classes("text-xs")
                            ui.button(icon="close", on_click=lambda i=i: remove_file(i)).props(
                                "flat round dense size=xs color=grey-7")
                    if len(files) > 1:
                        ui.button("Clear all", icon="clear_all", on_click=lambda: clear_files()).props(
                            "flat dense no-caps size=sm")

        # ---- work area: review (left) + document preview (right) ----
        # CSS grid so the two panes sit side-by-side from the md breakpoint up
        # (and the column gap never causes wrap, unlike summed flex widths).
        work = ui.element("div").classes("w-full grid grid-cols-1 md:grid-cols-12 gap-4 items-start")
        with work:
            # LEFT: review table
            with ui.element("div").classes("md:col-span-5 min-w-0"):
                with ui.card().classes("w-full rounded-xl shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("Review").classes("text-base font-medium")
                        with ui.row().classes("items-center gap-1"):
                            summary = ui.label("").classes("text-sm font-medium").style(f"color:{PRIMARY}")
                            ui.button(icon="refresh", on_click=lambda: run_detection()).props(
                                "flat round dense").tooltip("Re-scan the loaded files with the current dictionary")
                    ui.label("Tick = redact · click a row to find it · fix the Type if wrong · ↻ re-scan after "
                             "editing the dictionary").classes("text-xs text-slate-500")
                    columns = [
                        {"name": "type", "label": "Type", "field": "type", "align": "left"},
                        {"name": "value", "label": "Detected value", "field": "value", "align": "left"},
                        {"name": "count", "label": "×", "field": "count", "align": "right"},
                        {"name": "source", "label": "Found by", "field": "source", "align": "left"},
                    ]
                    table = ui.table(columns=columns, rows=[], row_key="id",
                                     selection="multiple").classes("w-full").props("flat dense").style(
                        "max-height:60vh")
                    # editable type for name-like items; read-only badge for patterns
                    table.add_slot("body-cell-type", '''
                        <q-td :props="props">
                          <q-select v-if="['PERSON','COUNTERPARTY','OTHER'].includes(props.row.type)"
                            dense options-dense borderless v-model="props.row.type"
                            :options="['PERSON','COUNTERPARTY','OTHER']"
                            @update:model-value="() => $parent.$emit('typechange', props.row)"
                            style="min-width:120px" />
                          <q-badge v-else :color="props.row.type_color">{{ props.row.type }}</q-badge>
                        </q-td>''')
                    table.add_slot("body-cell-source", '''
                        <q-td :props="props">
                          <q-badge outline :color="props.row.source_color">{{ props.row.source_label }}</q-badge>
                        </q-td>''')

            # RIGHT: document preview
            with ui.element("div").classes("md:col-span-7 min-w-0"):
                with ui.card().classes("w-full rounded-xl shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("Document").classes("text-base font-medium")
                        file_select = ui.select(options=[], on_change=lambda e: on_preview_file(e)).props(
                            "outlined dense").style("min-width:180px")
                        file_select.visible = False
                    with ui.row().classes("items-center gap-2 w-full"):
                        manual_type = ui.select(options=["COUNTERPARTY", "PERSON", "OTHER"],
                                                value="COUNTERPARTY").props("outlined dense").style("width:160px")
                        ui.button("Redact selection", icon="visibility_off",
                                  on_click=lambda: redact_selection()).props("outline no-caps dense")
                    ui.label("Select any text in the document below, then click “Redact selection”.").classes(
                        "text-xs text-slate-500")
                    preview_html = ui.html("").classes("w-full")
        work.visible = False

        # ---- confirm ----
        confirm_card = ui.card().classes("w-full rounded-xl shadow-sm")
        with confirm_card:
            ui.label("Confirm & export").classes("text-base font-medium")
            with ui.row().classes("items-center gap-4 w-full"):
                pw = ui.input("Passphrase (optional)", password=True,
                              password_toggle_button=True).props("outlined dense").classes("flex-1")
                gen = ui.button("Generate de-identified file(s)", icon="bolt").props("unelevated no-caps")
            add_dict = ui.checkbox("Add newly-found names to my dictionary", value=True)
            ui.label("Blank passphrase = the reversal key is saved unprotected. You'll need the passphrase "
                     "(if set) + the Job ID to re-identify later.").classes("text-xs text-slate-500")
            result = ui.column().classes("w-full mt-1")
        confirm_card.visible = False

        # ---- handlers ----
        def refresh_table():
            items = state["items"]
            rows = []
            for i, it in enumerate(items):
                lbl, scol = SOURCE_BADGE.get(it.source, (it.source, "grey"))
                rows.append({"id": i, "type": it.type, "type_color": TYPE_COLOR.get(it.type, "grey"),
                             "value": it.canonical, "count": it.count, "source": it.source,
                             "source_label": lbl, "source_color": scol})
            table.rows = rows
            table.selected = [r for r in rows if items[r["id"]].include]
            table.update()
            has = bool(items)
            work.visible = has
            confirm_card.visible = has
            update_summary()
            render_preview()

        def update_summary():
            summary.text = f"{len(table.selected)} will be tokenised"

        table.on("selection", lambda e: update_summary())

        def on_row_click(e):
            try:
                iid = e.args[1]["id"]
            except (KeyError, IndexError, TypeError):
                return
            ui.run_javascript(
                "document.querySelectorAll('mark.hl.active').forEach(m=>m.classList.remove('active'));"
                f"var ms=document.querySelectorAll('mark.hl[data-iid=\"{iid}\"]');"
                "ms.forEach(m=>m.classList.add('active'));"
                "if(ms.length)ms[0].scrollIntoView({behavior:'smooth',block:'center'});")

        table.on("rowClick", on_row_click)

        def on_type_change(e):
            row = e.args[0] if isinstance(e.args, list) else e.args
            if not isinstance(row, dict):
                return
            iid, newtype = row.get("id"), row.get("type")
            items = state["items"]
            if iid is not None and 0 <= iid < len(items) and newtype:
                items[iid].type = newtype
                assign_tokens(items)
                refresh_table()

        table.on("typechange", on_type_change)

        def render_preview():
            if not files:
                preview_html.content = ""
                file_select.visible = False
                return
            names = [f["name"] for f in files]
            file_select.options = names
            file_select.visible = len(files) > 1
            idx = state["preview_idx"] if state["preview_idx"] < len(files) else 0
            state["preview_idx"] = idx
            if not file_select.value or file_select.value not in names:
                file_select.value = names[idx]
            f = files[idx]
            text = extract_text(f["data"], f["kind"])
            if f["kind"] == "xlsx":
                text = "(spreadsheet shown as text)\n\n" + text
            banner = ""
            warns = f.get("warnings")
            if warns:
                pages = ", ".join(str(w["page"]) for w in warns)
                banner = (f'<div class="pdf-warn">⚠ Page(s) {_html.escape(pages)} look image-based — '
                          "their text isn't extracted (no OCR), so any names on them are "
                          "<b>not redacted</b>. Check those pages in the original PDF.</div>")
            preview_html.content = banner + _preview_html(text, state["items"])

        def on_preview_file(e):
            if e.value in [f["name"] for f in files]:
                state["preview_idx"] = [f["name"] for f in files].index(e.value)
                render_preview()

        def run_detection():
            result.clear()
            if not files:
                state["items"] = []
                refresh_table()
                return
            combined = "\n\n".join(extract_text(f["data"], f["kind"]) for f in files)
            items = assign_tokens(detect(combined, load_entities() + manual_entities))
            manual_set = {e.canonical.lower() for e in manual_entities}
            for it in items:
                if it.source == "dictionary" and it.canonical.lower() in manual_set:
                    it.source = "manual"
            state["items"] = items
            refresh_table()

        async def on_file(e):
            f = e.file
            data = await f.read()
            kind = file_kind(f.name) or "txt"
            entry = {"name": f.name, "kind": kind, "data": data}
            if kind == "pdf":
                try:
                    entry["warnings"] = pdf_warnings(data)
                except Exception:
                    entry["warnings"] = []
            files.append(entry)
            render_files.refresh()
            run_detection()
            warns = entry.get("warnings")
            if warns:
                pages = ", ".join(str(w["page"]) for w in warns)
                ui.notify(f"⚠ {f.name}: page(s) {pages} look image-based — text/names there "
                          "can't be detected (no OCR). Review them in the original PDF.",
                          type="warning", multi_line=True, timeout=10000)
            else:
                ui.notify(f"Added {f.name}", color="primary")

        def on_sample():
            files.clear()
            manual_entities.clear()
            files.append({"name": "sample-memo.txt", "kind": "txt", "data": SAMPLE.encode("utf-8")})
            render_files.refresh()
            run_detection()
            ui.notify("Loaded sample memo", color="primary")

        def remove_file(i):
            del files[i]
            state["preview_idx"] = 0
            render_files.refresh()
            run_detection()

        def clear_files():
            files.clear()
            manual_entities.clear()
            state["preview_idx"] = 0
            render_files.refresh()
            run_detection()

        async def redact_selection():
            sel = await ui.run_javascript(
                'window.__deidSel || (window.getSelection?window.getSelection().toString():"")', timeout=5)
            sel = (sel or "").strip()
            if not sel:
                ui.notify("Select some text in the document first", color="warning")
                return
            if sel.lower() in {e.canonical.lower() for e in manual_entities}:
                ui.notify("Already added", color="warning")
                return
            manual_entities.append(Entity(canonical=sel, type=manual_type.value, aliases=[]))
            await ui.run_javascript('window.__deidSel="";if(window.getSelection)window.getSelection().removeAllRanges();')
            run_detection()
            ui.notify(f'Redacting “{sel[:40]}”', color="primary")

        def on_generate():
            if not files:
                ui.notify("Add a document first", color="warning")
                return
            items = state["items"]
            selected_ids = {r["id"] for r in table.selected}
            for i, it in enumerate(items):
                it.include = i in selected_ids
            assign_tokens(items)
            replace_fn, token_to_real = build_replacer(items)
            if not token_to_real:
                ui.notify("Nothing selected to redact", color="warning")
                return

            passphrase = pw.value or ""
            job_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
            created = datetime.now(timezone.utc).isoformat()
            sources = [f["name"] for f in files]
            outputs: dict[str, bytes] = {}
            total_hits = 0
            for f in files:
                out_bytes, ext, hits = redact_document(f["data"], f["kind"], replace_fn)
                base = f["name"].rsplit(".", 1)[0]
                outputs[f"{base}__deidentified{ext}"] = out_bytes
                total_hits += hits
            ref_bytes = _reference_text(job_id, created, sources, token_to_real)

            vault.save_job(job_id, token_to_real, passphrase,
                           meta={"source_file": ", ".join(sources), "replacements": total_hits})

            added = 0
            if add_dict.value:
                new_ents = [Entity(canonical=it.canonical, type=it.type,
                                   aliases=[s for s in it.surfaces if s != it.canonical])
                            for it in items
                            if it.include and it.source in ("suggestion", "manual")
                            and it.type in ("PERSON", "COUNTERPARTY")]
                if new_ents:
                    added = merge_entities(new_ents)

            result.clear()
            with result:
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    ui.icon("check_circle", color="positive")
                    ui.label(f"{total_hits} replacement(s) across {len(files)} file(s) · Job ID ").classes(
                        "text-sm")
                    ui.badge(job_id).props("color=primary")
                    if added:
                        ui.badge(f"+{added} to dictionary").props("color=teal-7")
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    if len(outputs) == 1:
                        name, data = next(iter(outputs.items()))
                        ui.button("Download de-identified file", icon="download",
                                  on_click=lambda d=data, n=name: ui.download(d, n)).props("unelevated no-caps")
                        ui.button("Download reference (.txt)", icon="description",
                                  on_click=lambda: ui.download(ref_bytes, f"{job_id}__reference.txt")).props(
                            "outline no-caps")
                    else:
                        bundle = dict(outputs)
                        bundle[f"{job_id}__reference.txt"] = ref_bytes
                        zipb = _zip_bytes(bundle)
                        ui.button(f"Download all {len(outputs)} files + reference (.zip)", icon="download",
                                  on_click=lambda z=zipb: ui.download(z, f"deidentified_{job_id}.zip")).props(
                            "unelevated no-caps")
                with ui.expansion("Show the sealed token → name mapping").classes("w-full"):
                    mcols = [{"name": "t", "label": "Token", "field": "t", "align": "left"},
                             {"name": "v", "label": "Real value", "field": "v", "align": "left"}]
                    ui.table(columns=mcols, rows=[{"t": t, "v": v} for t, v in token_to_real.items()]).props(
                        "flat dense").classes("w-full")
            ui.notify("De-identified file(s) ready", color="positive")

        gen.on("click", on_generate)


# ============================================================================
# 2 · RE-IDENTIFY
# ============================================================================
def build_reidentify_panel():
    sel: dict = {"job_id": None}
    upload: dict = {"data": None, "kind": None, "name": None}

    with ui.column().classes("w-full gap-5 pt-5"):
        with ui.card().classes("w-full rounded-xl shadow-sm"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Past conversions").classes("text-base font-medium")
                ui.button(icon="refresh", on_click=lambda: render_history.refresh()).props(
                    "flat round dense").tooltip("Refresh")
            ui.label("Pick the conversion you want to reverse.").classes("text-sm text-slate-500")
            hcols = [
                {"name": "created", "label": "When", "field": "created", "align": "left"},
                {"name": "source_file", "label": "Source file(s)", "field": "source_file", "align": "left"},
                {"name": "replacements", "label": "Redactions", "field": "replacements", "align": "right"},
                {"name": "job_id", "label": "Job ID", "field": "job_id", "align": "left"},
            ]
            htable = ui.table(columns=hcols, rows=[], row_key="job_id",
                              selection="single").classes("w-full").props("flat dense")

            @ui.refreshable
            def render_history():
                rows = []
                for h in vault.history():
                    rows.append({"job_id": h["job_id"],
                                 "created": (h["created"] or "").replace("T", " ")[:16],
                                 "source_file": h["source_file"] or "—",
                                 "replacements": h["replacements"]})
                htable.rows = rows
                htable.selected = [r for r in rows if r["job_id"] == sel["job_id"]]
                htable.update()

            def on_select(_):
                sel["job_id"] = htable.selected[0]["job_id"] if htable.selected else None
                selected_label.text = f"Selected: {sel['job_id']}" if sel["job_id"] else \
                    "Selected: none — click a row above."

            htable.on("selection", on_select)

        with ui.card().classes("w-full rounded-xl shadow-sm"):
            ui.label("Bring the real names back").classes("text-base font-medium")
            selected_label = ui.label("Selected: none — click a row above.").classes(
                "text-sm").style(f"color:{PRIMARY}")
            pw = ui.input("Passphrase (if one was set)", password=True,
                          password_toggle_button=True).props("outlined dense").classes("w-full")

            ui.label("Give it the AI's reply — upload the file to get the SAME format back, "
                     "or paste text.").classes("text-sm text-slate-500 mt-1")
            with ui.row().classes("items-center gap-2"):
                ui.upload(label="Upload the AI's .docx / .xlsx / .txt", auto_upload=True,
                          on_upload=lambda e: on_upload_ai(e)).props('accept=".docx,.xlsx,.txt" flat bordered')
                upload_note = ui.label("").classes("text-xs text-teal-700")
                clear_btn = ui.button(icon="close", on_click=lambda: clear_upload()).props(
                    "flat round dense color=grey-7").tooltip("Clear uploaded file")
                clear_btn.visible = False
            ai_text = ui.textarea("…or paste the AI output here").props("outlined").classes(
                "w-full").style("min-height:140px")
            ui.button("Re-identify", icon="lock_open", on_click=lambda: on_restore()).props(
                "unelevated no-caps")
            result = ui.column().classes("w-full")

        async def on_upload_ai(e):
            f = e.file
            upload.update(data=await f.read(), kind=file_kind(f.name) or "txt", name=f.name)
            upload_note.text = f"Will regenerate: {f.name}"
            clear_btn.visible = True
            ui.notify(f"Loaded {f.name} — will be regenerated in the same format", color="primary")

        def clear_upload():
            upload.update(data=None, kind=None, name=None)
            upload_note.text = ""
            clear_btn.visible = False
            ui.notify("Cleared uploaded file — will use pasted text", color="primary")

        def on_restore():
            if not sel["job_id"]:
                ui.notify("Select a conversion from the list above", color="warning")
                return
            if upload["data"] is None and not (ai_text.value or "").strip():
                ui.notify("Upload the AI's file or paste its text", color="warning")
                return
            try:
                job = vault.load_job(sel["job_id"], pw.value or "")
            except (ValueError, FileNotFoundError) as exc:
                ui.notify(str(exc), color="negative")
                return
            restore = build_restorer(job["mapping"])
            result.clear()
            if upload["data"] is not None:
                out_bytes, ext, hits = redact_document(upload["data"], upload["kind"], restore)
                base = upload["name"].rsplit(".", 1)[0]
                fname = f"{base}__reidentified{ext}"
                with result:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("check_circle", color="positive")
                        ui.label(f"Restored {hits} token(s) — file regenerated.").classes("text-sm")
                    ui.button(f"Download {fname}", icon="download",
                              on_click=lambda b=out_bytes, n=fname: ui.download(b, n)).props("unelevated no-caps")
            else:
                restored, hits = restore(ai_text.value or "")
                with result:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("check_circle", color="positive")
                        ui.label(f"Restored {hits} token(s).").classes("text-sm")
                    ui.textarea("Re-identified output", value=restored).props("outlined readonly").classes(
                        "w-full").style("min-height:140px")
                    ui.button("Download as .txt", icon="download",
                              on_click=lambda r=restored: ui.download(r.encode("utf-8"),
                                                                      f"{sel['job_id']}__reidentified.txt")).props(
                        "unelevated no-caps")
            ui.notify("Re-identified", color="positive")

        render_history()


# ============================================================================
# 3 · ENTITY DICTIONARY
# ============================================================================
def build_dictionary_panel():
    rows: list[dict] = [{"canonical": e.canonical, "type": e.type, "aliases": ", ".join(e.aliases)}
                        for e in load_entities()]

    with ui.column().classes("w-full gap-5 pt-5"):
        with ui.card().classes("w-full rounded-xl shadow-sm"):
            ui.label("Your known people & counterparties").classes("text-base font-medium")
            ui.label("A curated list is what makes detection reliable. Add aliases (short / legal / trading "
                     "names) so every variant maps to the same token.").classes("text-sm text-slate-500")
            editor = ui.column().classes("w-full gap-2 mt-2")

            @ui.refreshable
            def render_rows():
                editor.clear()
                with editor:
                    with ui.row().classes("w-full items-center text-xs text-slate-400 px-1"):
                        ui.label("Canonical name").classes("flex-1")
                        ui.label("Type").style("width:170px")
                        ui.label("Aliases (comma-separated)").classes("flex-1")
                        ui.label("").style("width:40px")
                    if not rows:
                        ui.label("No entities yet — add one below or bulk-import.").classes(
                            "text-sm text-slate-400 px-1 py-2")
                    for r in rows:
                        with ui.row().classes("w-full items-center gap-2"):
                            ui.input(value=r["canonical"],
                                     on_change=lambda e, r=r: r.update(canonical=e.value)).props(
                                "outlined dense").classes("flex-1")
                            ui.select(options=["PERSON", "COUNTERPARTY"], value=r["type"],
                                      on_change=lambda e, r=r: r.update(type=e.value)).props(
                                "outlined dense").style("width:170px")
                            ui.input(value=r["aliases"],
                                     on_change=lambda e, r=r: r.update(aliases=e.value)).props(
                                "outlined dense").classes("flex-1")
                            ui.button(icon="delete", on_click=lambda r=r: remove_row(r)).props(
                                "flat round dense color=grey-7").style("width:40px")

            def remove_row(r):
                rows.remove(r)
                render_rows.refresh()

            def add_row():
                rows.append({"canonical": "", "type": "COUNTERPARTY", "aliases": ""})
                render_rows.refresh()

            def save():
                ents, seen = [], set()
                for r in rows:
                    name = (r["canonical"] or "").strip()
                    if not name or name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    aliases = [a.strip() for a in (r["aliases"] or "").split(",") if a.strip()]
                    ents.append(Entity(canonical=name, type=(r["type"] or "COUNTERPARTY"), aliases=aliases))
                save_entities(ents)
                ui.notify(f"Saved {len(ents)} entit(ies)", color="positive")

            def reload_dict():
                rows.clear()
                rows.extend({"canonical": e.canonical, "type": e.type, "aliases": ", ".join(e.aliases)}
                            for e in load_entities())
                render_rows.refresh()
                ui.notify("Reloaded from disk", color="primary")

            render_rows()
            with ui.row().classes("gap-2 mt-2"):
                ui.button("Add entity", icon="add", on_click=add_row).props("outline no-caps")
                ui.button("Save dictionary", icon="save", on_click=save).props("unelevated no-caps")
                ui.button("Reload", icon="refresh", on_click=reload_dict).props("flat no-caps")

            with ui.expansion("Bulk import from a list").classes("w-full mt-1"):
                ui.label("Paste one name per line (e.g. your counterparty master list).").classes(
                    "text-sm text-slate-500")
                bulk = ui.textarea(label="Names").props("outlined").classes("w-full")
                btype = ui.select(options=["COUNTERPARTY", "PERSON"], value="COUNTERPARTY",
                                  label="Add as type").props("outlined dense").style("width:200px")

                def append_bulk():
                    have = {r["canonical"].strip().lower() for r in rows if r["canonical"].strip()}
                    added = 0
                    for line in (bulk.value or "").splitlines():
                        nm = line.strip()
                        if nm and nm.lower() not in have:
                            rows.append({"canonical": nm, "type": btype.value, "aliases": ""})
                            have.add(nm.lower())
                            added += 1
                    bulk.value = ""
                    render_rows.refresh()
                    ui.notify(f"Added {added} name(s) — remember to Save", color="primary")

                ui.button("Append to list", icon="playlist_add", on_click=append_bulk).props("outline no-caps")


# ============================================================================
# 4 · SETTINGS  (download detection-language models on demand)
# ============================================================================
def build_settings_panel():
    with ui.column().classes("w-full gap-5 pt-5"):
        with ui.card().classes("w-full rounded-xl shadow-sm"):
            ui.label("Detection languages").classes("text-base font-medium")
            ui.label("The app ships with English to stay small. Download an extra language only if you "
                     "need to auto-suggest names in that script — your dictionary works in every language "
                     "regardless. Downloading needs internet (one-off).").classes("text-sm text-slate-500")
            if not nlp_suggester.available():
                ui.label("⚠ The NLP suggestion engine isn't available in this build — only the dictionary "
                         "and patterns are active.").classes("text-sm text-amber-700 mt-1")
            lst = ui.column().classes("w-full gap-0 mt-2")

            @ui.refreshable
            def render():
                lst.clear()
                with lst:
                    for L in nlp_suggester.language_status():
                        with ui.row().classes("items-center gap-3 w-full border-b py-2"):
                            ui.label(L["label"]).classes("font-medium").style("width:110px")
                            ui.label(L["model"]).classes("text-xs text-slate-500").style("width:165px")
                            ui.label(L["size"]).classes("text-xs text-slate-400").style("width:70px")
                            ui.space()
                            if L["builtin"]:
                                ui.badge("Built-in", color="teal-7")
                            elif L["installed"]:
                                ui.badge("Installed", color="teal-7")
                                ui.button("Remove", icon="delete",
                                          on_click=lambda c=L["code"], n=L["label"]: do_remove(c, n)).props(
                                    "flat no-caps dense color=grey-7")
                            else:
                                ui.button("Download", icon="download",
                                          on_click=lambda c=L["code"], n=L["label"]: do_download(c, n)).props(
                                    "outline no-caps dense")

            async def do_download(code, label):
                note = ui.notification(f"Downloading {label} model… (this can take a minute)",
                                       spinner=True, timeout=None)
                ok, log = await run.io_bound(nlp_suggester.download_language, code)
                note.dismiss()
                if ok:
                    ui.notify(f"{label} model installed — now active for {label} text", color="positive")
                else:
                    ui.notify(f"Couldn't install {label} (no internet, or blocked). See the console window.",
                              color="negative", multi_line=True)
                    print(f"\n[language download: {label}] FAILED:\n{log}\n")
                render.refresh()

            async def do_remove(code, label):
                note = ui.notification(f"Removing {label} model…", spinner=True, timeout=None)
                ok, log = await run.io_bound(nlp_suggester.remove_language, code)
                note.dismiss()
                ui.notify(f"{label} removed" if ok else f"Couldn't remove {label}",
                          color="positive" if ok else "negative")
                if not ok:
                    print(f"\n[language remove: {label}] FAILED:\n{log}\n")
                render.refresh()

            render()
        with ui.card().classes("w-full rounded-xl shadow-sm"):
            ui.label("About Lethe").classes("text-base font-medium")
            ui.html(ABOUT_HTML)


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="Lethe — Document De-identifier", port=8731, reload=False, show=True,
           storage_secret="deident-local", favicon="web_static/favicon.svg")
