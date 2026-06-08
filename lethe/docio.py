"""
Document read / write.

extract_text(...)  -> plain text for the detection + review step.
redact_document(...) -> writes a de-identified file IN THE SAME FORMAT where
                        possible (.docx, .xlsx), preserving structure. PDFs are
                        extracted to a de-identified .docx because PDFs can't be
                        safely edited in place -- and a clean text/docx is what
                        you feed an AI anyway.
"""
from __future__ import annotations

import io
import os

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

try:
    import pdfplumber  # better reading order + table extraction
    _HAS_PDFPLUMBER = True
except Exception:  # pragma: no cover - optional, falls back to pypdf
    _HAS_PDFPLUMBER = False

# A page that carries a raster image yet yields fewer than this many words is
# treated as image-based (a scan, or a figure/chart with baked-in text) — names
# rendered as pixels can't be extracted, so they can't be detected or redacted.
# Gating on an actual image avoids false-flagging legitimately short text pages.
_IMAGE_PAGE_WORD_THRESHOLD = 20


def file_kind(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {".docx": "docx", ".pdf": "pdf", ".xlsx": "xlsx", ".txt": "txt"}.get(ext, "")


# ---- PDF page model ---------------------------------------------------------
def _read_pdf(data: bytes) -> list[dict]:
    """Parse a PDF into per-page content, preserving page boundaries.

    Each page -> {n, narrative, tables, n_words, n_images} where `narrative` is
    the flowing text *outside* any detected table and `tables` is a list of
    grids (list of rows of cell strings). Uses pdfplumber when available for
    reading order + table detection; otherwise falls back to flat pypdf text.
    """
    if _HAS_PDFPLUMBER:
        pages: list[dict] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                try:
                    found = page.find_tables()
                except Exception:
                    found = []
                bboxes = [t.bbox for t in found]

                def _outside(obj, _bboxes=bboxes):
                    cx = (obj["x0"] + obj["x1"]) / 2
                    cy = (obj["top"] + obj["bottom"]) / 2
                    return not any(x0 <= cx <= x1 and top <= cy <= bottom
                                   for (x0, top, x1, bottom) in _bboxes)

                try:
                    narrative = (page.filter(_outside).extract_text() if bboxes
                                 else page.extract_text()) or ""
                except Exception:
                    narrative = page.extract_text() or ""

                tables: list[list[list[str]]] = []
                for t in found:
                    try:
                        rows = t.extract()
                    except Exception:
                        continue
                    norm = [[(c or "").strip() for c in row] for row in rows if any(row)]
                    if norm:
                        tables.append(norm)

                n_words = len(narrative.split()) + sum(
                    len(c.split()) for tb in tables for row in tb for c in row)
                pages.append({"n": i, "narrative": narrative, "tables": tables,
                              "n_words": n_words, "n_images": len(page.images or [])})
        return pages

    # Fallback: pypdf flat text, page by page (no tables, page anchors kept).
    reader = PdfReader(io.BytesIO(data))
    out = []
    for i, page in enumerate(reader.pages, 1):
        txt = page.extract_text() or ""
        out.append({"n": i, "narrative": txt, "tables": [],
                    "n_words": len(txt.split()), "n_images": 0})
    return out


def pdf_warnings(data: bytes) -> list[dict]:
    """Pages that look image-based: they carry a raster image but almost no
    extractable text, so names rendered in those images are NOT detected or
    redacted — there is no OCR."""
    return [{"page": pg["n"], "words": pg["n_words"], "images": pg["n_images"]}
            for pg in _read_pdf(data)
            if pg["n_images"] > 0 and pg["n_words"] < _IMAGE_PAGE_WORD_THRESHOLD]


# ---- extraction (for detection) ---------------------------------------------
def extract_text(data: bytes, kind: str) -> str:
    if kind == "txt":
        return data.decode("utf-8", errors="replace")
    if kind == "docx":
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        for section in doc.sections:
            for hdrftr in (section.header, section.footer):
                parts.extend(p.text for p in hdrftr.paragraphs)
        return "\n".join(parts)
    if kind == "xlsx":
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        parts = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                parts.extend(str(c) for c in row if c is not None)
        return "\n".join(parts)
    if kind == "pdf":
        parts = []
        for pg in _read_pdf(data):
            parts.append(f"Page {pg['n']}")
            if pg["narrative"]:
                parts.append(pg["narrative"])
            for tb in pg["tables"]:
                for row in tb:
                    parts.append("\t".join(row))
        return "\n".join(parts)
    raise ValueError(f"Unsupported kind: {kind}")


# ---- redacted output --------------------------------------------------------
def _redact_paragraph(paragraph, replace_fn) -> int:
    """Replace text in a paragraph. If anything changes we flatten the
    paragraph's runs into one (formatting within a changed line is lost, but the
    redaction is guaranteed correct -- the right trade-off for a privacy gate)."""
    original = paragraph.text
    if not original:
        return 0
    new, hits = replace_fn(original)
    if hits and new != original:
        for run in list(paragraph.runs):
            run.text = ""
        if paragraph.runs:
            paragraph.runs[0].text = new
        else:
            paragraph.add_run(new)
    return hits


def _redact_docx(data: bytes, replace_fn) -> tuple[bytes, int]:
    doc = Document(io.BytesIO(data))
    hits = 0
    for p in doc.paragraphs:
        hits += _redact_paragraph(p, replace_fn)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    hits += _redact_paragraph(p, replace_fn)
    for section in doc.sections:
        for hdrftr in (section.header, section.footer):
            for p in hdrftr.paragraphs:
                hits += _redact_paragraph(p, replace_fn)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), hits


def _redact_xlsx(data: bytes, replace_fn) -> tuple[bytes, int]:
    wb = load_workbook(io.BytesIO(data))  # keep formulas/formatting
    hits = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    new, n = replace_fn(cell.value)
                    if n:
                        cell.value = new
                        hits += n
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), hits


def _text_to_docx(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_to_docx(pages: list[dict], replace_fn) -> tuple[bytes, int]:
    """Rebuild a de-identified .docx from parsed PDF pages, preserving page
    boundaries (a `Page N` heading + page break per source page) and tables
    (rendered as real Word tables). Page anchors let downstream tools quote
    against the original PDF pages."""
    doc = Document()
    intro = doc.add_paragraph()
    run = intro.add_run(
        "De-identified from PDF. The “Page N” headings below mark the "
        "original PDF pages; quote against those, not this document's own pagination.")
    run.italic = True

    hits = 0
    for idx, pg in enumerate(pages):
        if idx > 0:
            doc.add_page_break()
        doc.add_heading(f"Page {pg['n']}", level=2)

        if pg["narrative"]:
            new, n = replace_fn(pg["narrative"])
            hits += n
            for line in new.split("\n"):
                doc.add_paragraph(line)

        for tb in pg["tables"]:
            ncols = max((len(row) for row in tb), default=0)
            if not ncols:
                continue
            table = doc.add_table(rows=0, cols=ncols)
            try:
                table.style = "Table Grid"
            except Exception:
                pass
            for row in tb:
                cells = table.add_row().cells
                for ci in range(ncols):
                    val = row[ci] if ci < len(row) else ""
                    if val:
                        new, n = replace_fn(val)
                        hits += n
                        cells[ci].text = new
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), hits


def redact_document(data: bytes, kind: str, replace_fn) -> tuple[bytes, str, int]:
    """Return (output_bytes, output_extension, hit_count)."""
    if kind == "docx":
        out, hits = _redact_docx(data, replace_fn)
        return out, ".docx", hits
    if kind == "xlsx":
        out, hits = _redact_xlsx(data, replace_fn)
        return out, ".xlsx", hits
    if kind == "txt":
        new, hits = replace_fn(data.decode("utf-8", errors="replace"))
        return new.encode("utf-8"), ".txt", hits
    if kind == "pdf":
        out, hits = _pdf_to_docx(_read_pdf(data), replace_fn)
        return out, ".docx", hits
    raise ValueError(f"Unsupported kind: {kind}")
