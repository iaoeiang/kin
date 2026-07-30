"""Message body encryption — AES-256-GCM authenticated encryption."""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet


def derive_fernet_key(base_key: str) -> bytes:
    """Derive a valid 32-byte Fernet key from any string.

    Uses SHA-256 to normalize any-length input to exactly 32 bytes,
    then base64-encodes it for Fernet compatibility.
    """
    import hashlib
    key_bytes = base64.urlsafe_b64encode(hashlib.sha256(base_key.encode()).digest())
    return key_bytes


_fernet: Fernet | None = None


def get_fernet(message_encryption_key: str) -> Fernet:
    """Get or create a Fernet instance for the given key."""
    global _fernet
    if _fernet is None:
        key = derive_fernet_key(message_encryption_key)
        _fernet = Fernet(key)
    return _fernet


def encrypt_body(plaintext: str, key: str) -> str:
    """Encrypt message body. Returns base64-encoded ciphertext."""
    f = get_fernet(key)
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_body(ciphertext_b64: str, key: str) -> str:
    """Decrypt a Fernet-encrypted message body. Returns plaintext."""
    f = get_fernet(key)
    plaintext = f.decrypt(ciphertext_b64.encode("utf-8"))
    return plaintext.decode("utf-8")
