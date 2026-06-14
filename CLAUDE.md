# Lethe — notes for AI agents

Project memory lives in [`.claude/memory/`](.claude/memory/). Read
[`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) first for the index, then the
linked files for details. Add new persistent facts there (not under any per-user path)
so they travel with the repo.

Lethe is a fully-local, reversible document de-identifier (NiceGUI app). The thin
`app.py` is the UI; the `lethe/` package holds the engine. Aimed at non-technical
business users — keep the in-app Guide and README current with any feature change.
