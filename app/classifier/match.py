"""Fuzzy-match normalized text against a list of known gambling-promo patterns."""

_MIN_FUZZY_PATTERN_LEN = 4


def find_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if pattern in text:
            return pattern

    for pattern in patterns:
        if len(pattern) >= _MIN_FUZZY_PATTERN_LEN and _fuzzy_contains(text, pattern):
            return pattern

    return None


def _fuzzy_contains(text: str, pattern: str) -> bool:
    window_lengths = {len(pattern) - 1, len(pattern), len(pattern) + 1}
    for length in window_lengths:
        if length <= 0:
            continue
        for start in range(0, len(text) - length + 1):
            window = text[start:start + length]
            if _edit_distance_at_most_one(window, pattern):
                return True
    return False


def _edit_distance_at_most_one(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False

    if len(a) == len(b):
        mismatches = sum(1 for x, y in zip(a, b) if x != y)
        return mismatches <= 1

    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    i = j = 0
    skipped = False
    while i < len(shorter) and j < len(longer):
        if shorter[i] == longer[j]:
            i += 1
            j += 1
            continue
        if skipped:
            return False
        skipped = True
        j += 1
    return True
