"""Persistence for the known-entity dictionary (people + counterparties)."""
from __future__ import annotations

import json
import os

from core import Entity

DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entities.json")


def load_entities() -> list[Entity]:
    if not os.path.exists(DICT_PATH):
        return []
    with open(DICT_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Entity(canonical=e["canonical"], type=e.get("type", "COUNTERPARTY"),
                   aliases=e.get("aliases", [])) for e in raw]


def save_entities(entities: list[Entity]) -> None:
    data = [{"canonical": e.canonical, "type": e.type, "aliases": e.aliases} for e in entities]
    with open(DICT_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def merge_entities(new_entities: list[Entity]) -> int:
    """Add new entities to the saved dictionary (dedup by canonical name,
    case-insensitive; merge any new aliases into an existing entry).
    Returns the number of brand-new entities added."""
    ents = load_entities()
    keys = {e.canonical.strip().lower(): e for e in ents}
    added = 0
    for ne in new_entities:
        k = ne.canonical.strip().lower()
        if not k:
            continue
        if k in keys:
            ex = keys[k]
            have = {a.lower() for a in ex.aliases} | {k}
            for a in ne.aliases:
                if a.strip() and a.strip().lower() not in have:
                    ex.aliases.append(a.strip())
                    have.add(a.strip().lower())
        else:
            ents.append(ne)
            keys[k] = ne
            added += 1
    save_entities(ents)
    return added
