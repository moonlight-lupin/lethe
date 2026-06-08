"""
Encrypted, reversible mapping store.

Each de-identification "job" produces a mapping of token -> real value.
That mapping is the ONLY way to re-identify the AI's output later, so it is
encrypted at rest with a passphrase (PBKDF2 -> Fernet). Lose the passphrase
and the mapping is unrecoverable by design.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from . import APP_ROOT

VAULT_DIR = os.path.join(APP_ROOT, "vault")


def _ensure_dir() -> None:
    os.makedirs(VAULT_DIR, exist_ok=True)


def _key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def save_job(job_id: str, mapping: dict, passphrase: str, meta: dict | None = None) -> str:
    """Encrypt and persist a token->realvalue mapping. Returns the file path."""
    _ensure_dir()
    salt = os.urandom(16)
    fernet = Fernet(_key_from_passphrase(passphrase, salt))
    payload = {
        "job_id": job_id,
        "created": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
        "mapping": mapping,
    }
    token = fernet.encrypt(json.dumps(payload).encode("utf-8"))
    record = {"salt": base64.b64encode(salt).decode("ascii"), "ciphertext": token.decode("ascii")}
    path = os.path.join(VAULT_DIR, f"{job_id}.vault.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    _append_index({
        "job_id": job_id,
        "created": payload["created"],
        "source_file": (meta or {}).get("source_file", ""),
        "replacements": (meta or {}).get("replacements", 0),
    })
    return path


def load_job(job_id: str, passphrase: str) -> dict:
    """Decrypt a job. Raises ValueError on a wrong passphrase."""
    path = os.path.join(VAULT_DIR, f"{job_id}.vault.json")
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    salt = base64.b64decode(record["salt"])
    fernet = Fernet(_key_from_passphrase(passphrase, salt))
    try:
        plain = fernet.decrypt(record["ciphertext"].encode("ascii"))
    except InvalidToken as exc:
        raise ValueError("Wrong passphrase, or the vault file is corrupted.") from exc
    return json.loads(plain.decode("utf-8"))


def list_jobs() -> list[str]:
    if not os.path.isdir(VAULT_DIR):
        return []
    return sorted(f[: -len(".vault.json")] for f in os.listdir(VAULT_DIR) if f.endswith(".vault.json"))


# ---- conversion history index ------------------------------------------------
# A small, UNENCRYPTED list of non-secret fields (job id, date, source filename,
# count) so users can recognise which job to re-identify. The sensitive part --
# the token -> real-name mapping -- stays encrypted in the .vault.json files.
INDEX_PATH = os.path.join(VAULT_DIR, "index.json")


def _read_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return []


def _append_index(entry: dict) -> None:
    idx = _read_index()
    idx.append(entry)
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        json.dump(idx, fh, indent=2)


def history() -> list[dict]:
    """Every saved job, newest first, enriched with index metadata where present.
    Jobs created before the index existed still appear (id + date from filename)."""
    idx = {e.get("job_id"): e for e in _read_index()}
    out = []
    for jid in list_jobs():
        e = idx.get(jid, {})
        created = e.get("created", "")
        if not created and len(jid) >= 15 and jid[8] == "-":  # YYYYMMDD-HHMMSS-xxxx
            created = f"{jid[0:4]}-{jid[4:6]}-{jid[6:8]} {jid[9:11]}:{jid[11:13]}"
        out.append({"job_id": jid, "created": created,
                    "source_file": e.get("source_file", ""),
                    "replacements": e.get("replacements", "")})
    return sorted(out, key=lambda r: r["job_id"], reverse=True)
