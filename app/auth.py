import time

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models import User

SESSION_USER_ID_KEY = "user_id"

_MAX_FAILED_LOGINS = 5
_FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
# ponytail: in-memory, per-process; move to the DB if the app ever runs more than one worker
_failed_logins: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def get_current_user(request: Request, session: Session) -> User | None:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    if user_id is None:
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def login(request: Request, user: User) -> None:
    request.session[SESSION_USER_ID_KEY] = user.id


def logout(request: Request) -> None:
    request.session.pop(SESSION_USER_ID_KEY, None)


def _recent_failures(client_ip: str) -> list[float]:
    cutoff = time.monotonic() - _FAILED_LOGIN_WINDOW_SECONDS
    recent = [t for t in _failed_logins.get(client_ip, []) if t > cutoff]
    _failed_logins[client_ip] = recent
    return recent


def is_login_rate_limited(client_ip: str) -> bool:
    return len(_recent_failures(client_ip)) >= _MAX_FAILED_LOGINS


def record_failed_login(client_ip: str) -> None:
    _recent_failures(client_ip).append(time.monotonic())


def clear_failed_logins(client_ip: str) -> None:
    _failed_logins.pop(client_ip, None)
