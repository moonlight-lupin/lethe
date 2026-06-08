"""Lethe — the de-identification engine.

An importable package holding the detection/redaction core, document I/O, the
encrypted vault, the entity dictionary and the NLP suggester. The thin
``app.py`` at the project root is purely the NiceGUI user interface.

    from lethe import detect, assign_tokens, build_replacer, vault, ...
"""
from __future__ import annotations

import os

# The application root — the folder that holds app.py and the user's data
# (entities.json, the vault/ folder). It is the PARENT of this package dir, so
# data sits next to the app in both the dev tree and the portable build.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from . import core, docio, nlp_suggester, store, vault  # noqa: E402
from .core import (  # noqa: E402
    Entity,
    _whole_word_regex,
    assign_tokens,
    build_replacer,
    build_restorer,
    detect,
)
from .docio import extract_text, file_kind, pdf_warnings, redact_document  # noqa: E402
from .store import (  # noqa: E402
    load_entities,
    load_token_types,
    merge_entities,
    save_entities,
    save_token_types,
)

__all__ = [
    "APP_ROOT",
    # submodules
    "core", "docio", "nlp_suggester", "store", "vault",
    # core API
    "Entity", "assign_tokens", "build_replacer", "build_restorer", "detect",
    "_whole_word_regex",
    # document I/O
    "extract_text", "file_kind", "pdf_warnings", "redact_document",
    # entity dictionary
    "load_entities", "merge_entities", "save_entities",
    # user-defined token types
    "load_token_types", "save_token_types",
]
