import sqlite3

from app.backup import backup


def test_backup_copies_db_and_keeps_only_newest(tmp_path):
    db = tmp_path / "app.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (42)")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for i in range(3):
        (backup_dir / f"antijudolinator-2000010{i}-000000.db").write_bytes(b"")

    target = backup(str(db), keep=2)

    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT x FROM t").fetchone() == (42,)
    assert sorted(p.name for p in backup_dir.iterdir()) == [
        "antijudolinator-20000102-000000.db",
        target.name,
    ]
