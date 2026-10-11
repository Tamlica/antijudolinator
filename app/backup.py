"""Snapshot the SQLite DB into a backups/ folder next to it, keeping the newest few.

Usage: python -m app.backup   (e.g. nightly: docker compose exec -T app python -m app.backup)
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import DB_PATH

KEEP = 7


def backup(db_path: str = DB_PATH, keep: int = KEEP) -> Path:
    backup_dir = Path(db_path).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    target = backup_dir / f"antijudolinator-{datetime.now():%Y%m%d-%H%M%S}.db"

    source = sqlite3.connect(db_path)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)  # consistent copy even while the app is writing
    finally:
        dest.close()
        source.close()

    for old in sorted(backup_dir.glob("antijudolinator-*.db"))[:-keep]:
        old.unlink()
    return target


if __name__ == "__main__":
    print(f"Backed up to {backup()}")
