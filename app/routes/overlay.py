from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db import get_session
from app.models import User
from app.ws_manager import manager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/overlay/{overlay_token}")
def overlay_page(
    overlay_token: str, request: Request, session: Session = Depends(get_session)
):
    user = session.scalar(select(User).where(User.overlay_token == overlay_token))
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown overlay token")
    return templates.TemplateResponse(
        request, "overlay.html", {"overlay_token": overlay_token}
    )


@router.websocket("/ws/overlay/{overlay_token}")
async def overlay_socket(websocket: WebSocket, overlay_token: str):
    await manager.connect(overlay_token, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(overlay_token, websocket)
