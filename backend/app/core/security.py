from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.database import get_db
from app.core.logging import logger

# ── Password hashing ───────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ── JWT tokens ─────────────────────────────────────────────────────────────────

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: Typically the user's ID or username.
        expires_delta: Custom expiry duration. Falls back to settings value.
        extra_claims: Additional payload claims to embed.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT token, returning structured claims."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub: Optional[str] = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return TokenData(user_id=int(sub) if sub.isdigit() else None, username=sub)
    except JWTError as exc:
        logger.warning(f"JWT decode error: {exc}")
        raise credentials_exception from exc


# ── Fernet field-level encryption ──────────────────────────────────────────────

def _get_fernet() -> Fernet:
    """Return a Fernet instance, generating and caching a key if needed.

    In production, FERNET_KEY should be set as a stable environment variable.
    """
    key = settings.FERNET_KEY
    if not key:
        # Generate a key in-memory for dev. Encrypted values will not survive
        # restarts unless FERNET_KEY is persisted in .env.
        generated = Fernet.generate_key()
        logger.warning(
            "FERNET_KEY not set – using ephemeral key. Encrypted fields will "
            "be unreadable after restart. Set FERNET_KEY in .env to persist."
        )
        return Fernet(generated)
    return Fernet(key.encode() if isinstance(key, str) else key)


_fernet: Optional[Fernet] = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


def encrypt_field(value: str) -> str:
    """Encrypt a plaintext string and return a URL-safe base64 ciphertext."""
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a Fernet ciphertext. Raises HTTPException on failure."""
    try:
        return get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        logger.error("Failed to decrypt field – key mismatch or corrupted data.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not decrypt sensitive field.",
        ) from exc


# ── Current user dependency ────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency resolving the authenticated user from a Bearer token."""
    from app.models.user import User  # avoid circular import at module level

    token_data = decode_access_token(token)

    stmt = select(User).where(
        (User.id == token_data.user_id) | (User.username == token_data.username)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


async def get_current_active_superuser(current_user=Depends(get_current_user)):
    """Dependency that additionally asserts the user has superuser privileges."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges",
        )
    return current_user
