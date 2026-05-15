from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Application user with authentication credentials."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # One-to-one relationship with user settings
    settings: Mapped["UserSettings | None"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username} active={self.is_active}>"


class UserSettings(Base):
    """Per-user integration credentials stored with field-level encryption.

    Sensitive fields (telegram_token, mt5_password) are encrypted via Fernet
    before persistence and must be decrypted via app.core.security.decrypt_field.
    """

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Telegram ─────────────────────────────────────────────────────────────
    # Stored as Fernet ciphertext
    telegram_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── MetaTrader 5 ──────────────────────────────────────────────────────────
    mt5_login: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Stored as Fernet ciphertext
    mt5_password: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mt5_server: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mt5_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── TradingView ───────────────────────────────────────────────────────────
    tradingview_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Risk overrides ────────────────────────────────────────────────────────
    max_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_drawdown_percent: Mapped[float | None] = mapped_column(
        nullable=True, comment="Override global MAX_DRAWDOWN_PERCENT"
    )
    default_lot_size: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="settings")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_settings_user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserSettings id={self.id} user_id={self.user_id}>"
