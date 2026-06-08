import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lethe import core, docio, store, vault  # noqa: F401
from lethe import (Entity, assign_tokens, build_replacer, build_restorer,
                   detect)

text = (
    "Dear Mr John Smith,\n"
    "Acme Capital Partners (Acme) confirms the transaction with Meridian Holdings Pte Ltd.\n"
    "Contact: john.smith@acme.com or +65 6789 1234. Account 1234-5678-9012.\n"
    "Regards, Jane Doe"
)

ents = [
    Entity("John Smith", "PERSON", ["Smith", "Mr Smith"]),
    Entity("Acme Capital Partners", "COUNTERPARTY", ["Acme"]),
]

items = assign_tokens(detect(text, ents))
for it in items:
    flag = "x" if it.include else " "
    print(f"[{flag}] {it.type:13} {it.token:18} <- {it.canonical!r}  (x{it.count}) [{it.source}]")

repl, t2r = build_replacer(items)
red, hits = repl(text)
print("\n--- REDACTED (", hits, "hits) ---")
print(red)

restore = build_restorer(t2r)
back, n = restore(red)
print("\n--- RESTORED (", n, "hits) --- John Smith back:", "John Smith" in back, "| Acme back:", "Acme" in back)

# vault round-trip
path = vault.save_job("test-job", t2r, "hunter2", meta={"x": 1})
loaded = vault.load_job("test-job", "hunter2")
print("\nVault OK:", loaded["mapping"] == t2r)
try:
    vault.load_job("test-job", "wrongpw")
    print("Vault wrong-pw guard: FAILED")
except ValueError:
    print("Vault wrong-pw guard: OK")
import os
os.remove(path)
