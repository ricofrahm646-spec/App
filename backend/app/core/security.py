from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings


class TokenManager:
    """Handles JWT creation and verification."""

    @staticmethod
    def create_access_token(
        data: dict[str, Any],
        expires_delta: timedelta | None = None,
    ) -> str:
        settings = get_settings()
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta
            or timedelta(minutes=settings.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def verify_token(token: str) -> dict[str, Any] | None:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
            return payload
        except JWTError:
            return None


class EncryptionManager:
    """Handles symmetric encryption/decryption of sensitive data."""

    def __init__(self) -> None:
        settings = get_settings()
        key = settings.encryption_key
        if not key:
            key = Fernet.generate_key().decode()
        elif len(key) != 44:
            key = b64encode(hashlib.sha256(key.encode()).digest()).decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            return None


class APIKeyManager:
    """Generates and validates API keys for webhook / service auth."""

    PREFIX = "jrv"
    KEY_LENGTH = 32

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Return (full_key, hashed_key) pair."""
        raw = secrets.token_urlsafe(cls.KEY_LENGTH)
        full_key = f"{cls.PREFIX}_{raw}"
        hashed = cls._hash_key(full_key)
        return full_key, hashed

    @classmethod
    def verify_key(cls, provided_key: str, stored_hash: str) -> bool:
        computed = cls._hash_key(provided_key)
        return hmac.compare_digest(computed, stored_hash)

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()


class SecureStorage:
    """In-memory encrypted key-value store for runtime secrets."""

    def __init__(self) -> None:
        self._encryptor = EncryptionManager()
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = self._encryptor.encrypt(value)

    def get(self, key: str) -> str | None:
        encrypted = self._store.get(key)
        if encrypted is None:
            return None
        return self._encryptor.decrypt(encrypted)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return key in self._store

    def keys(self) -> list[str]:
        return list(self._store.keys())


def generate_webhook_signature(payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
