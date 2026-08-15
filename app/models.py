import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _random_token() -> str:
    return secrets.token_urlsafe(24)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    webhook_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_random_token
    )
    overlay_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_random_token
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="user")


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_text: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    supporter: Mapped[str] = mapped_column(String(255))
    amount: Mapped[int] = mapped_column(Integer, default=0)
    raw_message: Mapped[str] = mapped_column(String(2000))
    normalized_message: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(16))  # "clean" | "gambling"
    matched_pattern_id: Mapped[int | None] = mapped_column(
        ForeignKey("patterns.id"), nullable=True
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    review_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")
