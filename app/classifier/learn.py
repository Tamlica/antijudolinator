"""Extract candidate gambling-promo patterns from a confirmed message."""

from sqlalchemy.orm import Session

from app.classifier.normalize import words
from app.classifier.store import reinforce_pattern
from app.models import Message

_MIN_TOKEN_LEN = 3

_STOPWORDS = {
    # Indonesian filler/common words
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ini", "itu",
    "saya", "kamu", "kita", "kami", "semoga", "terima", "kasih", "makasih",
    "semangat", "selalu", "sukses", "semua", "terus", "selamat", "malam",
    "pagi", "siang", "sore", "kak", "min", "bang", "ya", "banget", "aja",
    "juga", "sama", "biar", "supaya", "terimakasih", "wa",
    # English filler/common words
    "the", "and", "for", "to", "is", "this", "that", "you", "thanks",
    "thank",
}


def extract_candidate_patterns(raw_message: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for token in words(raw_message):
        if len(token) < _MIN_TOKEN_LEN or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        candidates.append(token)
    return candidates


def learn_from_confirmation(session: Session, message: Message) -> None:
    for pattern_text in extract_candidate_patterns(message.raw_message):
        reinforce_pattern(session, pattern_text, message.user_id)
