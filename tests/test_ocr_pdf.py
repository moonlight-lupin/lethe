"""OCR round-trip: a PDF whose names exist only as PIXELS (a simulated scan)
must still be detected and redacted when the local OCR engine is installed.
Skips cleanly when liteparse isn't available (base install)."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lethe import (Entity, assign_tokens, build_replacer, detect, extract_text,
                   ocr_available, pdf_warnings, redact_document)

if not ocr_available():
    print("SKIP: liteparse not installed — image pages are warned, not read")
    sys.exit(0)

from docx import Document
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

# ---- build: page 1 native text, page 2 image-only (names as pixels) ----------
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36) \
    if os.path.exists("C:/Windows/Fonts/arial.ttf") else ImageFont.load_default(36)
img = Image.new("RGB", (1400, 700), "white")
d = ImageDraw.Draw(img)
d.text((60, 80),  "CONFIDENTIAL MEMO (scanned copy)", font=font, fill="black")
d.text((60, 200), "Counterparty: Acme Capital Partners", font=font, fill="black")
d.text((60, 300), "Lead: John Smith", font=font, fill="black")
ibuf = io.BytesIO(); img.save(ibuf, format="PNG"); ibuf.seek(0)

pdf = FPDF()
pdf.add_page(); pdf.set_font("Helvetica", size=12)
pdf.multi_cell(0, 8, "Page one mentions Meridian Holdings in native text.")
pdf.add_page(); pdf.image(ibuf, x=5, y=20, w=200)
data = bytes(pdf.output())

# ---- OCR'd extraction + warnings ---------------------------------------------
text = extract_text(data, "pdf")
assert "Acme Capital Partners" in text and "John Smith" in text, "OCR text missing"
warns = pdf_warnings(data)
print("warnings:", warns)
assert any(w["page"] == 2 and w["ocr"] for w in warns), "page 2 should be marked ocr=True"
assert not any(not w["ocr"] for w in warns), "no hard warnings expected"

# ---- redact ---------------------------------------------------------------
ents = [Entity("Acme Capital Partners", "COUNTERPARTY", ["Acme"]),
        Entity("John Smith", "PERSON", []),
        Entity("Meridian Holdings", "COUNTERPARTY", [])]
repl, t2r = build_replacer(assign_tokens(detect(text, ents)))
out, ext, hits = redact_document(data, "pdf", repl)
doc_text = "\n".join(p.text for p in Document(io.BytesIO(out)).paragraphs)
print("ext:", ext, "hits:", hits)
leaks = [n for n in ("Acme Capital Partners", "John Smith", "Meridian Holdings")
         if n in doc_text]
print("leaks:", leaks or "none", "| tokens present:",
      "[COUNTERPARTY_001]" in doc_text and "[PERSON_001]" in doc_text)
assert not leaks and hits >= 3
print("OCR PDF OK — pixel-only names detected, redacted, and page marked for review")
