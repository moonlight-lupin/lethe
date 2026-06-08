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
import zipfile
from datetime import datetime, timezone

from nicegui import run, ui

import nlp_suggester
import vault
from core import Entity, assign_tokens, build_replacer, build_restorer, detect, _whole_word_regex
from docio import extract_text, file_kind, redact_document
from store import load_entities, merge_entities, save_entities

# ---- look & feel -------------------------------------------------------------
PRIMARY = "#72263d"  # deep burgundy
ui.colors(primary=PRIMARY, secondary="#3a1420", accent="#a3526a",
          positive="#15803d", dark="#1a0e13")

TYPE_COLOR = {"PERSON": "teal-7", "COUNTERPARTY": "deep-purple-6", "OTHER": "pink-7",
              "EMAIL": "blue-grey-6", "PHONE": "blue-grey-6", "ACCOUNT": "blue-grey-6"}
SOURCE_BADGE = {"dictionary": ("Known entity", "teal-7"),
                "pattern": ("Pattern", "blue-grey-6"),
                "suggestion": ("Suggested", "amber-8"),
                "manual": ("Manual", "pink-7")}

PREVIEW_CSS = """
<style>
body{background:#f7f5f6}
.doc-preview{white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.7;
  max-height:62vh;overflow:auto;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}
mark.hl{border-radius:3px;padding:0 1px}
mark.hl-PERSON{background:#ccfbf1}
mark.hl-COUNTERPARTY{background:#ede9fe}
mark.hl-OTHER{background:#fce7f3}
mark.hl-EMAIL,mark.hl-PHONE,mark.hl-ACCOUNT{background:#e2e8f0}
mark.hl.active{outline:2px solid #72263d;background:#fde68a}
::selection{background:#fbcfe8}
.guide-md{font-size:.9rem;line-height:1.55;color:#334155}
.guide-md h1,.guide-md h2,.guide-md h3{font-weight:600;color:#72263d;margin:.9rem 0 .25rem}
.guide-md h1{font-size:1.15rem}
.guide-md h2{font-size:1.05rem}
.guide-md h3{font-size:1rem}
.guide-md p{margin:.35rem 0}
.guide-md ul{margin:.2rem 0 .2rem 1.1rem;list-style:disc}
.guide-md li{margin:.12rem 0}
.guide-md code{background:#f1f5f9;padding:0 3px;border-radius:3px;font-size:.85em}
</style>
"""

GUIDE_MD = """
### What this tool does
Replaces real people & counterparty names with placeholder tokens (like
`[PERSON_001]`, `[COUNTERPARTY_001]`) **before** you send a document to an AI —
then puts the real names back into the AI's reply. Everything runs on this
computer; nothing is ever sent anywhere.

### 1 · De-identify
1. Drag in one or more **Word / PDF / Excel** files (or click *Try a sample memo*).
2. The right pane shows the document with detected names **highlighted**
   (teal = person, purple = counterparty, grey = email/phone/account).
3. In the **Review** list:
   - **Tick** what to remove. (Suggestions are off by default.)
   - **Click a row** to jump to it in the document.
   - Fix a wrong **Type** using its dropdown.
   - Missed something? **Select the text** in the document, then **Redact selection**.
   - Edited your dictionary? Press **↻** to re-scan.
4. Optionally set a **passphrase**, then **Generate**. You get the de-identified
   file(s), a **reference** list of tokens, and a **Job ID**.

### 2 · Re-identify
1. Pick the conversion from **Past conversions**.
2. Enter the passphrase (if you set one).
3. **Upload the AI's reply file** (same format back) *or* paste its text.
4. Click **Re-identify** — the real names are restored.

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
- **Scanned / image-only PDFs** — no selectable text, so nothing is found.
- Text in **shapes, text boxes, charts or embedded objects**, and document
  **metadata, comments or tracked changes** — these may still carry names.
- Amounts, dates and ID numbers — unless they match the email / phone / account patterns.

Always glance over the document preview before sending — your dictionary and your
review are the real safeguard.

### Good to know
- **Keep your passphrase + Job ID together** — you need both to reverse a job.
- A **blank passphrase** means the reversal key is saved unprotected.
- **PDFs** come back as Word; **spreadsheets** keep their format.
- Nothing leaves this machine — no internet, no cloud.
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
    ui.add_head_html(PREVIEW_CSS)
    # remember the last text selection inside the preview, even after a click
    ui.add_body_html("<script>document.addEventListener('mouseup',function(){"
                     "try{var s=window.getSelection().toString();"
                     "if(s&&s.trim())window.__deidSel=s;}catch(e){}});</script>")

    guide = _guide_dialog()
    with ui.header(elevated=False).classes("items-center justify-between px-6 py-3"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon("verified_user", size="26px").classes("opacity-90")
            with ui.column().classes("gap-0"):
                ui.label("Document De-identifier").classes(
                    "text-lg font-semibold leading-tight whitespace-nowrap")
                ui.label("Remove people & counterparties before sending to AI").classes(
                    "text-xs opacity-80 leading-tight")
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.button("Guide", icon="help_outline", on_click=guide.open).props("flat no-caps").classes("text-white")
            ui.chip("Local · offline", icon="lock").props("outline").classes("text-white")

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
            preview_html.content = _preview_html(text, state["items"])

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
            files.append({"name": f.name, "kind": file_kind(f.name) or "txt", "data": await f.read()})
            render_files.refresh()
            run_detection()
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
            ui.label("About").classes("text-base font-medium")
            ui.label("Document De-identifier · runs fully on this machine · no data leaves your computer.").classes(
                "text-sm text-slate-500")


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="Document De-identifier", port=8731, reload=False, show=True,
           storage_secret="deident-local", favicon="🛡️")
