"""Symmetric encryption helper for secrets (LLM keys, Telegram token, MT5 password)."""
from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = settings.encryption_key.strip()
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key
    return Fernet(key_bytes)


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
