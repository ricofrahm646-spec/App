"""Security utilities for the JARVIS Trading OS.

Provides helpers for:
- Fernet-based symmetric encryption / decryption of API keys and credentials.
- Password hashing and verification via bcrypt (passlib).
- JWT access-token creation and validation (python-jose).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Fernet encryption helpers
# ---------------------------------------------------------------------------


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a valid 32-byte URL-safe-base64 Fernet key from an arbitrary string."""
    digest = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key(settings.ENCRYPTION_KEY))


def encrypt_value(value: str) -> str:
    """Encrypt a plaintext string and return the cipher-text as a UTF-8 string."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token back to plaintext.

    Raises ``cryptography.fernet.InvalidToken`` on failure.
    """
    return _get_fernet().decrypt(token.encode()).decode()


def encrypt_api_key(api_key: str) -> str:
    """Convenience alias – encrypts an API key / credential for DB storage."""
    return encrypt_value(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Convenience alias – decrypts an API key / credential retrieved from DB."""
    return decrypt_value(encrypted_key)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    data:
        Payload claims (e.g. ``{"sub": "user@example.com"}``).
    expires_delta:
        Custom lifetime.  Defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES`` from
        settings.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the payload dict on success.

    Raises
    ------
    jose.JWTError
        If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])


def generate_api_key() -> str:
    """Generate a cryptographically-secure random API key (64 hex chars)."""
    return secrets.token_hex(32)
