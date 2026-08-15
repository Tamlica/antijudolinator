from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classifier.classify import classify_message
from app.db import get_session
from app.models import Message, User
from app.overlay_template import DEFAULT_TEMPLATE, render_overlay_html
from app.ws_manager import manager

router = APIRouter()


class SociabuzzPayload(BaseModel):
    message: str
    amount: int = 0
    supporter: str = ""


@router.post("/webhook/sociabuzz/{webhook_token}")
async def receive_sociabuzz_donation(
    webhook_token: str,
    payload: SociabuzzPayload,
    session: Session = Depends(get_session),
):
    user = session.scalar(
        select(User).where(User.webhook_token == webhook_token, User.is_active.is_(True))
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown webhook token")

    result = classify_message(session, payload.message)

    message = Message(
        user_id=user.id,
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
        rendered_html = render_overlay_html(
            user.overlay_template or DEFAULT_TEMPLATE,
            message.supporter,
            message.amount,
            message.raw_message,
        )
        await manager.push(user.overlay_token, {"html": rendered_html})

    return {"status": message.status, "message_id": message.id}
