---
name: restore-tab
description: Lethe's "Restore" tab — manual re-identify for documents tokenised outside Lethe
metadata:
  type: project
---

Lethe has a **Restore** tab (`build_restore_panel` in [app.py](../../app.py)), added 2026-06-15:
re-identify a document full of `[bracketed]` tokens when the de-identification happened
**outside Lethe** (another tool, a colleague, by hand) so there is no vault Job ID.

Flow: upload/paste → scan with `_RESTORE_TOKEN_RE` (`\[[^\[\]\r\n]{1,80}\]`) → review table
(bare numeric tokens like `[1]` auto-unticked as footnotes) → fill real values →
`build_restorer(map)` + `redact_document` rebuild in the same format (PDF → Word).

Opt-in "Add to dictionary" uses `_infer_entity_type()`: token prefix → PERSON / COUNTERPARTY
(or a registered custom type); pattern tokens (EMAIL/PHONE/ACCOUNT) and free-form
placeholders return None and are skipped, so the dictionary isn't polluted. Also doubles as a
template filler. Tested in `tests/test_restore.py`. Docs updated per [[keep-docs-in-sync]].
