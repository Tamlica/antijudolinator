import sqlalchemy as sa

from app.db import _ensure_column


def test_ensure_column_adds_missing_column(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)"))

    _ensure_column(engine, "users", "overlay_template", "TEXT")

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
    assert "overlay_template" in columns


def test_ensure_column_is_idempotent_when_already_present(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig2.db'}")
    with engine.begin() as conn:
        conn.execute(
            sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, overlay_template TEXT)")
        )

    _ensure_column(engine, "users", "overlay_template", "TEXT")  # must not raise

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
    assert "overlay_template" in columns
