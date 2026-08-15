"""One-off CLI: create the first admin account from environment variables.

Usage: python -m app.bootstrap_admin
"""

import os
import sys

from app.auth import hash_password
from app.db import SessionLocal, init_db
from app.models import User


def main() -> None:
    username = os.environ.get("ADMIN_BOOTSTRAP_USERNAME")
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if not username or not password:
        print("ADMIN_BOOTSTRAP_USERNAME and ADMIN_BOOTSTRAP_PASSWORD must be set", file=sys.stderr)
        raise SystemExit(1)

    init_db()
    session = SessionLocal()
    try:
        existing = session.query(User).filter_by(username=username).first()
        if existing is not None:
            print(f"User '{username}' already exists — nothing to do.")
            return
        admin = User(username=username, password_hash=hash_password(password), role="admin")
        session.add(admin)
        session.commit()
        print(f"Created admin user '{username}'.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
