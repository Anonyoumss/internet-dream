"""AES-256-GCM envelope encryption with PBKDF2-derived keys."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_ITERATIONS = 600_000
_KEY_DIR = Path.home() / ".internet-dream"
_SALT_FILE = _KEY_DIR / "salt"
_KEY_FILE = _KEY_DIR / "key"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def get_or_create_key(passphrase: str | None = None) -> AESGCM:
    """Load or create the local data-encryption key.

    If `passphrase` is given it is used directly (salt persisted alongside).
    Otherwise an existing key file is used; a random key is generated on
    first run so the store works out of the box (documented in README).
    """
    _KEY_DIR.mkdir(parents=True, exist_ok=True)

    if passphrase:
        if _SALT_FILE.exists():
            salt = _SALT_FILE.read_bytes()
        else:
            salt = os.urandom(16)
            _SALT_FILE.write_bytes(salt)
        os.chmod(_SALT_FILE, 0o600)
        return AESGCM(_derive_key(passphrase, salt))

    if _KEY_FILE.exists():
        return AESGCM(_KEY_FILE.read_bytes())

    key = AESGCM.generate_key(bit_length=256)
    _KEY_FILE.write_bytes(key)
    os.chmod(_KEY_FILE, 0o600)
    return AESGCM(key)
