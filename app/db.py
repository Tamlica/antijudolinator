import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

DB_PATH = os.environ.get("DB_PATH", "./antijudolinator.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _ensure_column(engine: Engine, table: str, column: str, ddl_type: str) -> None:
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def init_db() -> None:
    Base.metadata.create_all(engine)
    _ensure_column(engine, "users", "overlay_template", "TEXT")
    _ensure_column(engine, "users", "alert_duration_seconds", "INTEGER NOT NULL DEFAULT 8")
    _ensure_column(engine, "users", "alert_sound_url", "VARCHAR(512)")
    _ensure_column(engine, "users", "alert_volume", "INTEGER NOT NULL DEFAULT 80")
    _ensure_column(engine, "users", "tts_enabled", "BOOLEAN NOT NULL DEFAULT 0")
    _ensure_column(engine, "users", "tts_min_amount", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(engine, "messages", "external_id", "VARCHAR(128)")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_user_external_id "
            "ON messages (user_id, external_id)"
        ))


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
