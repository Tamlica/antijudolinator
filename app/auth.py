from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models import User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_USER_ID_KEY = "user_id"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def get_current_user(request: Request, session: Session) -> User | None:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    if user_id is None:
        return None
    return session.get(User, user_id)


def login(request: Request, user: User) -> None:
    request.session[SESSION_USER_ID_KEY] = user.id


def logout(request: Request) -> None:
    request.session.pop(SESSION_USER_ID_KEY, None)
