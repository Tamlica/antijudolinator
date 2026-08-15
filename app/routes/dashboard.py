from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import get_current_user, get_user_by_username, login, logout, verify_password
from app.classifier.learn import learn_from_confirmation
from app.db import get_session
from app.models import Message, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_login(request: Request, session: Session = Depends(get_session)) -> User:
    user = get_current_user(request, session)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = get_user_by_username(session, username)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid credentials"}, status_code=401
        )
    login(request, user)
    destination = "/admin/users" if user.role == "admin" else "/dashboard"
    return RedirectResponse(destination, status_code=303)


@router.post("/logout")
def logout_submit(request: Request):
    logout(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/dashboard")
def dashboard_page(
    request: Request,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    pending = session.scalars(
        select(Message)
        .where(Message.user_id == user.id, Message.status == "gambling", Message.reviewed.is_(False))
        .order_by(Message.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request, "dashboard.html", {"user": user, "pending": pending}
    )


@router.post("/dashboard/messages/{message_id}/confirm-gambling")
def confirm_gambling(
    message_id: int,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    message = _get_own_message(session, message_id, user)
    learn_from_confirmation(session, message)
    message.reviewed = True
    message.review_result = "confirmed_gambling"
    session.commit()
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/dashboard/messages/{message_id}/confirm-clean")
def confirm_clean(
    message_id: int,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    message = _get_own_message(session, message_id, user)
    message.reviewed = True
    message.review_result = "confirmed_clean"
    session.commit()
    return RedirectResponse("/dashboard", status_code=303)


def _get_own_message(session: Session, message_id: int, user: User) -> Message:
    message = session.get(Message, message_id)
    if message is None or message.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.get("/dashboard/history")
def history_page(
    request: Request,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    reviewed = session.scalars(
        select(Message)
        .where(Message.user_id == user.id, Message.reviewed.is_(True))
        .order_by(Message.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request, "history.html", {"user": user, "reviewed": reviewed}
    )


@router.get("/dashboard/settings")
def settings_page(request: Request, user: User = Depends(require_login)):
    base_url = str(request.base_url).rstrip("/")
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": user,
            "webhook_url": f"{base_url}/webhook/sociabuzz/{user.webhook_token}",
            "overlay_url": f"{base_url}/overlay/{user.overlay_token}",
        },
    )
