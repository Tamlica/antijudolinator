import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db import DB_PATH, get_session
from app.models import User
from app.templating import templates
from app.ws_manager import manager

router = APIRouter()

# Lives next to the DB so it's inside the Docker data volume.
SOUND_UPLOAD_DIR = Path(DB_PATH).parent / "uploads" / "sounds"
UPLOADED_SOUND_PREFIX = "/uploads/sounds/"
SOUND_FILENAME_RE = re.compile(r"^\d+-[0-9a-f]{16}\.(mp3|wav|ogg)$")


@router.get("/uploads/sounds/{filename}")
def uploaded_sound(filename: str):
    path = SOUND_UPLOAD_DIR / filename
    if not SOUND_FILENAME_RE.match(filename) or not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path)


@router.get("/overlay/{overlay_token}")
def overlay_page(
    overlay_token: str, request: Request, session: Session = Depends(get_session)
):
    user = session.scalar(select(User).where(User.overlay_token == overlay_token))
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown overlay token")
    nonce = secrets.token_urlsafe(16)
    # The user's template is inserted as HTML; this blocks any script in it
    # (including inline handlers like onerror=) while allowing CSS and images.
    csp = f"script-src 'nonce-{nonce}'; object-src 'none'; base-uri 'none'"
    return templates.TemplateResponse(
        request,
        "overlay.html",
        {"overlay_token": overlay_token, "nonce": nonce},
        headers={"Content-Security-Policy": csp},
    )


@router.websocket("/ws/overlay/{overlay_token}")
async def overlay_socket(
    websocket: WebSocket, overlay_token: str, session: Session = Depends(get_session)
):
    known = session.scalar(select(User.id).where(User.overlay_token == overlay_token))
    session.close()
    if known is None:
        await websocket.close(code=4404)
        return
    await manager.connect(overlay_token, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(overlay_token, websocket)
