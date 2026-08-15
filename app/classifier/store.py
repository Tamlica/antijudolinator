"""Pattern-store DB access: the shared, ever-growing list of known patterns."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classifier.seed_patterns import SEED_PATTERNS
from app.models import Pattern


def seed_if_empty(session: Session) -> None:
    if session.scalar(select(Pattern.id).limit(1)) is not None:
        return
    for pattern_text in SEED_PATTERNS:
        session.add(Pattern(pattern_text=pattern_text, created_by_user_id=None))
    session.commit()


def list_pattern_texts(session: Session) -> list[str]:
    rows = session.scalars(select(Pattern.pattern_text)).all()
    return sorted(rows, key=len, reverse=True)


def get_pattern_by_text(session: Session, pattern_text: str) -> Pattern | None:
    return session.scalar(select(Pattern).where(Pattern.pattern_text == pattern_text))


def reinforce_pattern(session: Session, pattern_text: str, user_id: int) -> Pattern:
    pattern = get_pattern_by_text(session, pattern_text)
    if pattern is None:
        pattern = Pattern(pattern_text=pattern_text, created_by_user_id=user_id, match_count=1)
        session.add(pattern)
    else:
        pattern.match_count += 1
    session.commit()
    session.refresh(pattern)
    return pattern
