"""Lethe — the de-identification engine.

An importable package holding the detection/redaction core, document I/O, the
encrypted vault, the entity dictionary and the NLP suggester. The thin
``app.py`` at the project root is purely the NiceGUI user interface.

    from lethe import detect, assign_tokens, build_replacer, vault, ...
"""
from __future__ import annotations

import os
import sys

# Bundled web assets (Cinzel font + favicon), served by the UI from /static.
# Resolved relative to this package so it works whether Lethe is run from a
# source checkout, the portable Windows bundle, or a pip/pipx install.
WEB_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_static")


def _resolve_data_dir() -> str:
    """Where the user's data lives — the entity dictionary (entities.json),
    custom token types and the encrypted vault/ folder.

    Order: $LETHE_DATA_DIR (the Windows portable bundle sets this to keep data
    in-folder), else the per-user application-data directory for the OS — so a
    pip/pipx install writes to the user's home, never into site-packages.
    """
    env = os.environ.get("LETHE_DATA_DIR")
    if env:
        return env
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:  # Linux / *nix
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "Lethe")


DATA_DIR = _resolve_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)

from . import core, docio, nlp_suggester, store, vault  # noqa: E402
from .core import (  # noqa: E402
    Entity,
    _whole_word_regex,
    assign_tokens,
    build_replacer,
    build_restorer,
    detect,
)
from .docio import (  # noqa: E402
    download_ocr_language,
    extract_text,
    file_kind,
    installed_ocr_languages,
    ocr_available,
    pdf_warnings,
    read_xlsx_grid,
    redact_document,
    remove_ocr_language,
)
from .store import (  # noqa: E402
    load_entities,
    load_token_types,
    merge_entities,
    save_entities,
    save_token_types,
)

__all__ = [
    "DATA_DIR", "WEB_STATIC",
    # submodules
    "core", "docio", "nlp_suggester", "store", "vault",
    # core API
    "Entity", "assign_tokens", "build_replacer", "build_restorer", "detect",
    "_whole_word_regex",
    # document I/O
    "extract_text", "file_kind", "ocr_available", "pdf_warnings", "read_xlsx_grid",
    "redact_document",
    # offline OCR language data
    "download_ocr_language", "installed_ocr_languages", "remove_ocr_language",
    # entity dictionary
    "load_entities", "merge_entities", "save_entities",
    # user-defined token types
    "load_token_types", "save_token_types",
]
