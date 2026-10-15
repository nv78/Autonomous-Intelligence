"""Encryption for user-supplied LLM provider API keys (BYOK)."""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

PROVIDERS = ("anthropic", "openai", "google")


def _derived_key() -> str:
    # Stable key derived from JWT_SECRET_KEY so local/dev setups don't need a
    # second secret. Production must set PROVIDER_KEY_ENCRYPTION_KEY.
    secret = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()).decode()


def _fernet() -> MultiFernet:
    """Encrypt with the configured key; still decrypt values written with the
    JWT-derived fallback key, so setting PROVIDER_KEY_ENCRYPTION_KEY later
    doesn't strand keys that were stored before it existed."""
    keys = [k for k in (os.environ.get("PROVIDER_KEY_ENCRYPTION_KEY", ""), _derived_key()) if k]
    unique = list(dict.fromkeys(keys))
    return MultiFernet([Fernet(k.encode()) for k in unique])


def encrypt_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "*" * len(plaintext)
    return f"{plaintext[:4]}...{plaintext[-4:]}"


def get_user_provider_key(user_id: int, provider: str) -> str | None:
    """Look up and decrypt a user's own key for `provider`, or None if unset.

    Any DB error here (e.g. the database is unreachable) falls back to None
    rather than propagating — a user-supplied key is an optional override,
    and its absence should never break the server's own configured key.
    """
    from database.db import get_connection, get_provider_key

    try:
        cnx = get_connection()
        try:
            encrypted = get_provider_key(cnx, user_id, provider)
        finally:
            cnx.close()
    except Exception:
        return None
    if not encrypted:
        return None
    try:
        return decrypt_key(encrypted)
    except InvalidToken:
        return None
