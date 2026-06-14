---
name: keep-docs-in-sync
description: When adding/changing a Lethe feature, update the in-app Guide and README in the same pass
metadata:
  type: feedback
---

When a user-facing feature is added or changed in Lethe, update **both** the in-app
Guide (`GUIDE_MD` in [app.py](../../app.py)) and the **README** as part of the same change —
don't treat docs as a follow-up.

**Why:** Lethe is aimed at non-technical business users; the Guide and README are the
primary way they discover what each tab does. The user has explicitly asked for this more
than once.

**How to apply:** For a new tab/mode, add a numbered section to `GUIDE_MD` (renumber the
sections after it), add a "How it works — the tabs" entry in the README (renumber the
later tabs), and add a Key features bullet. Verify the live app renders before considering
the feature done. See [restore-tab](restore-tab.md).
