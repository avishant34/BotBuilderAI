from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="mixed")
    bots_created_today: Mapped[int] = mapped_column(Integer, default=0)
    last_generation_date: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeneratedBot(Base):
    __tablename__ = "generated_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    bot_name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64), default="other")
    idea: Mapped[str] = mapped_column(Text)
    requirements_json: Mapped[str] = mapped_column(Text)
    files_json: Mapped[str] = mapped_column(Text)
    review_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_safe: Mapped[bool] = mapped_column(Boolean, default=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversationContext(Base):
    """Store ongoing generation session context for multi-turn flows."""
    __tablename__ = "conversation_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(64), default="idle")
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
