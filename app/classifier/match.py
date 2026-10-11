"""Match a message's normalized words against known gambling-promo patterns.

Matching is word-based so a pattern can't straddle two real words
("smart people" must not match "rtp"). Short patterns are the riskiest, so:
- every pattern matches a whole word, or two adjacent words joined ("sl ot");
- patterns of 4+ chars also match the start/end of a word ("slotgacor");
- patterns of 5+ chars also match anywhere inside a word, or one edit away.
"""

_MIN_AFFIX_LEN = 4
_MIN_LONG_LEN = 5


def find_match(tokens: list[str], patterns: list[str]) -> str | None:
    joined_pairs = [a + b for a, b in zip(tokens, tokens[1:])]

    for pattern in patterns:
        if pattern in tokens or pattern in joined_pairs:
            return pattern
        if len(pattern) >= _MIN_AFFIX_LEN and any(
            t.startswith(pattern) or t.endswith(pattern) for t in tokens
        ):
            return pattern
        if len(pattern) >= _MIN_LONG_LEN and any(pattern in t for t in tokens + joined_pairs):
            return pattern

    for pattern in patterns:
        if len(pattern) >= _MIN_LONG_LEN and any(_fuzzy_contains(t, pattern) for t in tokens):
            return pattern

    return None


def _fuzzy_contains(token: str, pattern: str) -> bool:
    length = len(pattern)
    # Deletions only for 6+ chars: a 5-char pattern minus one letter is a common 4-letter chunk.
    window_lengths = {length, length + 1} | ({length - 1} if length >= 6 else set())
    for window_length in window_lengths:
        for start in range(0, len(token) - window_length + 1):
            if _edit_distance_at_most_one(token[start:start + window_length], pattern):
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
