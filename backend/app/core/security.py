"""Token and secret handling using Fernet at rest."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_fernet_key() -> bytes:
    if settings.fernet_key:
        return settings.fernet_key.encode()
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt_secret(plain: str) -> str:
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return get_fernet().decrypt(token.encode()).decode()


def generate_fernet_key() -> str:
    """Run once in deployment to set JARVIS_FERNET_KEY."""
    return Fernet.generate_key().decode()
