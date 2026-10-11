from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import get_user_by_username, hash_password
from app.db import get_session
from app.models import Message, Pattern, User
from app.routes.dashboard import require_login

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _users_page(request: Request, admin: User, session: Session, error: str | None = None):
    users = session.scalars(select(User).order_by(User.created_at)).all()
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {"admin": admin, "users": users, "error": error},
        status_code=400 if error else 200,
    )


@router.get("/users")
def list_users(
    request: Request,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return _users_page(request, admin, session)


@router.post("/users")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    username = username.strip()
    if get_user_by_username(session, username) is not None:
        return _users_page(request, admin, session, f"Username '{username}' is already taken.")
    user = User(username=username, password_hash=hash_password(password), role="user")
    session.add(user)
    session.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-active")
def toggle_active(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = _get_user(session, user_id)
    user.is_active = not user.is_active
    session.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/password")
def reset_password(
    user_id: int,
    new_password: str = Form(..., min_length=8),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = _get_user(session, user_id)
    user.password_hash = hash_password(new_password)
    session.commit()
    return RedirectResponse("/admin/users", status_code=303)


def _get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/patterns")
def list_patterns(
    request: Request,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(Pattern, User.username)
        .outerjoin(User, Pattern.created_by_user_id == User.id)
        .order_by(Pattern.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request, "admin_patterns.html", {"admin": admin, "patterns": rows}
    )


@router.post("/patterns/{pattern_id}/delete")
def delete_pattern(
    pattern_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    pattern = session.get(Pattern, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    session.execute(
        update(Message).where(Message.matched_pattern_id == pattern_id).values(matched_pattern_id=None)
    )
    session.delete(pattern)
    session.commit()
    return RedirectResponse("/admin/patterns", status_code=303)
