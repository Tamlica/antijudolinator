from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classifier.classify import classify_message
from app.db import get_session
from app.models import Message, User
from app.overlay_template import build_alert_payload
from app.ws_manager import manager

router = APIRouter()


class SociabuzzPayload(BaseModel):
    id: str | None = None
    message: str
    amount: int = 0
    supporter: str = ""


# Sync handler: FastAPI runs it in a worker thread, so the DB work and pattern
# scan don't block the event loop that serves the overlay WebSockets.
@router.post("/webhook/sociabuzz/{webhook_token}")
def receive_sociabuzz_donation(
    webhook_token: str,
    payload: SociabuzzPayload,
    session: Session = Depends(get_session),
):
    user = session.scalar(
        select(User).where(User.webhook_token == webhook_token, User.is_active.is_(True))
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown webhook token")

    if payload.id is not None:
        existing = session.scalar(
            select(Message).where(Message.user_id == user.id, Message.external_id == payload.id)
        )
        if existing is not None:
            return {"status": existing.status, "message_id": existing.id, "duplicate": True}

    result = classify_message(session, payload.message)

    message = Message(
        user_id=user.id,
        external_id=payload.id,
        supporter=payload.supporter,
        amount=payload.amount,
        raw_message=payload.message,
        normalized_message=result.normalized_message,
        status=result.status,
        matched_pattern_id=result.matched_pattern.id if result.matched_pattern else None,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    if result.status == "clean":
        alert = build_alert_payload(user, message.supporter, message.amount, message.raw_message)
        from_thread.run(manager.push, user.overlay_token, alert)

    return {"status": message.status, "message_id": message.id}
