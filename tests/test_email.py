"""Email & HTML ingestion: .eml / .html (and .msg when extract-msg is present)
come in, a de-identified Word (.docx) goes out. The header block
(From / To / Cc / Subject) carries names + addresses, so it is de-identified
along with the body."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email.message import EmailMessage

from docx import Document

from lethe import (Entity, assign_tokens, build_replacer, detect,
                   extract_text, file_kind, redact_document)

ents = [Entity("John Smith", "PERSON", ["Smith"]),
        Entity("Acme Capital Partners", "COUNTERPARTY", ["Acme"]),
        Entity("Jane Doe", "PERSON", [])]
NAMES = ("John Smith", "Acme Capital Partners", "Jane Doe")


def redact(data, kind):
    text = extract_text(data, kind)
    repl, _ = build_replacer(assign_tokens(detect(text, ents)))
    out, ext, hits = redact_document(data, kind, repl)
    return text, extract_text(out, "docx"), ext, hits


# ---- file_kind recognises the new extensions -------------------------------
assert file_kind("a.eml") == "eml"
assert file_kind("a.msg") == "msg"
assert file_kind("a.html") == "html" and file_kind("a.htm") == "html"

# ---- .eml: names in BOTH the headers and the body --------------------------
m = EmailMessage()
m["From"] = "John Smith <john.smith@acme.com>"
m["To"] = "Jane Doe <jane.doe@example.com>"
m["Subject"] = "Acme Capital Partners — deal update"
m.set_content("Hi Jane,\n\nJohn Smith here from Acme Capital Partners. "
              "Call me on +65 6789 1234.\n")
eml = m.as_bytes()

text, out_text, ext, hits = redact(eml, "eml")
assert "john.smith@acme.com" in text, "header address should be extracted for the EMAIL pattern"
assert ext == ".docx"
assert "From:" in out_text and "Subject:" in out_text, "labelled header block should render"
leaks = [n for n in (*NAMES, "john.smith@acme.com") if n in out_text]
print("eml hits:", hits, "leaks:", leaks or "none")
assert not leaks and hits >= 6   # John Smith x2, Acme x2, two emails (+phone)

# ---- .html: tags stripped, <script>/<style> skipped ------------------------
html = (b"<html><head><style>.x{color:red}</style></head><body>"
        b"<p>Dear <b>Jane Doe</b>,</p>"
        b"<p>Regards from <a href='mailto:john.smith@acme.com'>John Smith</a> "
        b"at Acme Capital Partners.</p>"
        b"<script>var secret=1;</script></body></html>")
htext = extract_text(html, "html")
assert all(n in htext for n in NAMES)
assert "var secret" not in htext, "<script> contents must be dropped"
_, out_text, ext, hits = redact(html, "html")
assert ext == ".docx"
leaks = [n for n in NAMES if n in out_text]
print("html hits:", hits, "leaks:", leaks or "none")
assert not leaks and hits >= 3

# ---- .msg path is wired (extract-msg is a base dependency) ------------------
try:
    import extract_msg
    print("extract_msg present:", extract_msg.__version__, "— .msg enabled")
except ImportError:
    print("NOTE: extract-msg not installed — .msg would be disabled")

print("EMAIL OK — eml/html ingested, headers + body de-identified, Word out")
