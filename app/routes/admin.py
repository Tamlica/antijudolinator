from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import get_current_user, hash_password
from app.db import get_session
from app.models import User

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def require_admin(request: Request, session: Session = Depends(get_session)) -> User:
    user = get_current_user(request, session)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/users")
def list_users(
    request: Request,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    users = session.scalars(select(User).order_by(User.created_at)).all()
    return templates.TemplateResponse(
        request, "admin_users.html", {"admin": admin, "users": users}
    )


@router.post("/users")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
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
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    session.commit()
    return RedirectResponse("/admin/users", status_code=303)
