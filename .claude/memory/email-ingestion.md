---
name: email-ingestion
description: Lethe ingests .eml / .msg / .html emails and outputs a de-identified Word doc
metadata:
  type: project
---

Lethe ingests email files (added 2026-06-16): `.eml`, Outlook `.msg`, and `.html`/`.htm`.
Like the PDF path, they can't be safely round-tripped, so they come in and a de-identified
**Word (.docx)** goes out (`redact_document` returns `.docx`).

In [docio.py](../../lethe/docio.py): `_parse_email(data, kind)` → `{headers, body}`; the
From/To/Cc/Date/Subject header block is extracted AND redacted along with the body (headers
carry the names + addresses Lethe targets). `_email_to_docx` builds the Word file with an
agent-facing notice + a bold-labelled header block. HTML→text is a dependency-free stdlib
`HTMLParser` subclass (`_html_to_text`); `.eml` uses stdlib `email`.

`.msg` needs **extract-msg**, which pulls a heavy transitive tree (RTFDE, oletools,
beautifulsoup4, msoffcrypto-tool…) — ~18 MB net (after cryptography, already a base dep).
So it's the optional **`[email]`** pip extra (in `pyproject.toml`), NOT a base dependency —
exactly mirroring how `liteparse`/`[ocr]` is handled: it's also listed in `requirements.txt`
so the Windows installer / portable bundle ship `.msg` out of the box, while a lean
`pipx install` reads `.eml`/`.html` and flags `.msg` with an actionable message
(`_parse_msg` raises pointing to `lethe[email]`). Attachments and inline images are NOT
read/redacted. Tested in `tests/test_email.py`. Docs updated per [[keep-docs-in-sync]].
