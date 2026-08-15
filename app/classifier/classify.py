from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.classifier.match import find_match
from app.classifier.normalize import normalize
from app.classifier.store import get_pattern_by_text, list_pattern_texts
from app.models import Pattern


@dataclass
class ClassificationResult:
    status: str  # "clean" | "gambling"
    normalized_message: str
    matched_pattern: Pattern | None


def classify_message(session: Session, raw_message: str) -> ClassificationResult:
    normalized = normalize(raw_message)
    patterns = list_pattern_texts(session)
    matched_text = find_match(normalized, patterns)

    if matched_text is None:
        return ClassificationResult("clean", normalized, None)

    matched_pattern = get_pattern_by_text(session, matched_text)
    return ClassificationResult("gambling", normalized, matched_pattern)
