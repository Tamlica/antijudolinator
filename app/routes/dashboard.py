import secrets
from pathlib import Path

from anyio import from_thread
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import (
    clear_failed_logins,
    get_current_user,
    get_user_by_username,
    hash_password,
    is_login_rate_limited,
    login,
    logout,
    record_failed_login,
    verify_password,
)
from app.classifier.learn import extract_candidate_patterns, learn_from_confirmation
from app.db import get_session
from app.models import Message, User, random_token
from app.overlay_template import (
    BUILTIN_SOUND_PREFIX,
    BUILTIN_SOUNDS,
    DEFAULT_TEMPLATE,
    MAX_TEMPLATE_LENGTH,
    PRESETS,
    PREVIEW_SAMPLE,
    build_alert_payload,
    render_overlay_html,
)
from app.routes.overlay import SOUND_UPLOAD_DIR, UPLOADED_SOUND_PREFIX
from app.ws_manager import manager

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
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(client_ip):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Too many failed attempts. Try again in 15 minutes."},
            status_code=429,
        )

    user = get_user_by_username(session, username)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        record_failed_login(client_ip)
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid credentials"}, status_code=401
        )
    clear_failed_logins(client_ip)
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
    pending_with_candidates = [
        (message, extract_candidate_patterns(message.raw_message)) for message in pending
    ]
    return templates.TemplateResponse(
        request, "dashboard.html", {"user": user, "pending": pending_with_candidates}
    )


@router.post("/dashboard/messages/{message_id}/confirm-gambling")
def confirm_gambling(
    message_id: int,
    learn_words: list[str] = Form(default=[]),
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    message = _get_own_message(session, message_id, user)
    learn_from_confirmation(session, message, learn_words)
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
def settings_page(
    request: Request, user: User = Depends(require_login), notice: str | None = None
):
    base_url = str(request.base_url).rstrip("/")
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": user,
            "webhook_url": f"{base_url}/webhook/sociabuzz/{user.webhook_token}",
            "overlay_url": f"{base_url}/overlay/{user.overlay_token}",
            "overlay_template": user.overlay_template or DEFAULT_TEMPLATE,
            "presets": PRESETS,
            "builtin_sounds": BUILTIN_SOUNDS,
            "sound_choice": _current_sound_choice(user.alert_sound_url),
            "max_template_length": MAX_TEMPLATE_LENGTH,
            "notice": _SETTINGS_NOTICES.get(notice),
        },
    )


def _current_sound_choice(sound_url: str | None) -> str:
    if sound_url is None:
        return "none"
    if sound_url.startswith(BUILTIN_SOUND_PREFIX):
        return "builtin:" + Path(sound_url).stem
    if sound_url.startswith(UPLOADED_SOUND_PREFIX):
        return "upload"
    return "url"


_SETTINGS_NOTICES = {  # key -> (text, is_error)
    "alert-saved": ("Alert settings saved.", False),
    "sound-missing-file": ("Choose a sound file to upload.", True),
    "sound-bad-file": ("Sound must be an .mp3, .wav or .ogg file under 1 MB.", True),
    "sound-bad-url": ("Sound URL must start with https://", True),
    "template-too-long": (f"Template is too long (max {MAX_TEMPLATE_LENGTH:,} characters).", True),
    "template-saved": ("Overlay design saved.", False),
    "test-sent": ("Test alert sent to your overlay.", False),
    "test-no-overlay": ("No overlay is connected. Is the OBS Browser Source open?", True),
    "password-changed": ("Password changed.", False),
    "password-wrong": ("Current password is incorrect.", True),
    "sociabuzz-token-saved": ("Sociabuzz token saved - webhooks without it are now rejected.", False),
    "sociabuzz-token-cleared": ("Sociabuzz token removed - webhooks are no longer verified.", True),
    "webhook-regenerated": ("New webhook URL generated - update it in sociabuzz.", False),
    "overlay-regenerated": ("New overlay URL generated - update your OBS Browser Source.", False),
}


@router.post("/dashboard/settings/password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(..., min_length=8),
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    if not verify_password(current_password, user.password_hash):
        return RedirectResponse("/dashboard/settings?notice=password-wrong", status_code=303)
    user.password_hash = hash_password(new_password)
    session.commit()
    return RedirectResponse("/dashboard/settings?notice=password-changed", status_code=303)


@router.post("/dashboard/settings/sociabuzz-token")
def save_sociabuzz_token(
    sociabuzz_webhook_token: str = Form("", max_length=128),
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    user.sociabuzz_webhook_token = sociabuzz_webhook_token.strip() or None
    session.commit()
    notice = "sociabuzz-token-saved" if user.sociabuzz_webhook_token else "sociabuzz-token-cleared"
    return RedirectResponse(f"/dashboard/settings?notice={notice}", status_code=303)


@router.post("/dashboard/settings/regenerate/{which}")
def regenerate_token(
    which: str,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    if which == "webhook":
        user.webhook_token = random_token()
    elif which == "overlay":
        user.overlay_token = random_token()
    else:
        raise HTTPException(status_code=404)
    session.commit()
    return RedirectResponse(f"/dashboard/settings?notice={which}-regenerated", status_code=303)


@router.post("/dashboard/settings/overlay-template")
def save_overlay_template(
    overlay_template: str = Form(""),
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    if len(overlay_template) > MAX_TEMPLATE_LENGTH:
        return RedirectResponse("/dashboard/settings?notice=template-too-long", status_code=303)
    user.overlay_template = overlay_template.strip() or None
    session.commit()
    return RedirectResponse("/dashboard/settings?notice=template-saved", status_code=303)


_MAX_SOUND_BYTES = 1024 * 1024
_SOUND_EXTENSIONS = {".mp3", ".wav", ".ogg"}


@router.post("/dashboard/settings/alert")
def save_alert_settings(
    alert_duration_seconds: int = Form(..., ge=3, le=60),
    alert_volume: int = Form(..., ge=0, le=100),
    sound_choice: str = Form("none"),
    sound_url: str = Form(""),
    sound_file: UploadFile | None = File(None),
    tts_enabled: bool = Form(False),
    tts_min_amount: int = Form(0, ge=0),
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    previous_sound = user.alert_sound_url

    if sound_choice == "none":
        user.alert_sound_url = None
    elif sound_choice.startswith("builtin:") and sound_choice[8:] in BUILTIN_SOUNDS:
        user.alert_sound_url = f"{BUILTIN_SOUND_PREFIX}{sound_choice[8:]}.wav"
    elif sound_choice == "url":
        sound_url = sound_url.strip()
        if not sound_url.startswith("https://") or len(sound_url) > 512:
            return RedirectResponse("/dashboard/settings?notice=sound-bad-url", status_code=303)
        user.alert_sound_url = sound_url
    elif sound_choice == "upload":
        if sound_file is not None and sound_file.filename:
            extension = Path(sound_file.filename).suffix.lower()
            data = sound_file.file.read(_MAX_SOUND_BYTES + 1)
            if extension not in _SOUND_EXTENSIONS or not data or len(data) > _MAX_SOUND_BYTES:
                return RedirectResponse("/dashboard/settings?notice=sound-bad-file", status_code=303)
            filename = f"{user.id}-{secrets.token_hex(8)}{extension}"
            SOUND_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            (SOUND_UPLOAD_DIR / filename).write_bytes(data)
            user.alert_sound_url = UPLOADED_SOUND_PREFIX + filename
        elif _current_sound_choice(previous_sound) != "upload":
            return RedirectResponse("/dashboard/settings?notice=sound-missing-file", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="Unknown sound choice")

    user.alert_duration_seconds = alert_duration_seconds
    user.alert_volume = alert_volume
    user.tts_enabled = tts_enabled
    user.tts_min_amount = tts_min_amount
    session.commit()

    if previous_sound != user.alert_sound_url and _current_sound_choice(previous_sound) == "upload":
        (SOUND_UPLOAD_DIR / Path(previous_sound).name).unlink(missing_ok=True)

    return RedirectResponse("/dashboard/settings?notice=alert-saved", status_code=303)


@router.post("/dashboard/settings/test-alert")
def send_test_alert(user: User = Depends(require_login)):
    alert = build_alert_payload(
        user, PREVIEW_SAMPLE["supporter"], PREVIEW_SAMPLE["amount"], PREVIEW_SAMPLE["message"]
    )
    delivered = from_thread.run(manager.push, user.overlay_token, alert)
    notice = "test-sent" if delivered else "test-no-overlay"
    return RedirectResponse(f"/dashboard/settings?notice={notice}", status_code=303)


@router.post("/dashboard/settings/overlay-template/preview")
def preview_overlay_template(
    template: str = Form(""),
    user: User = Depends(require_login),
):
    rendered = render_overlay_html(
        template,
        PREVIEW_SAMPLE["supporter"],
        PREVIEW_SAMPLE["amount"],
        PREVIEW_SAMPLE["message"],
    )
    return HTMLResponse(rendered)
