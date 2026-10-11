"""Normalize text so obfuscated gambling-promo messages fold to matchable words."""

import re
import unicodedata

_ZERO_WIDTH = {"​", "‌", "‍", "﻿"}

# Folded before splitting into words, since "$" and "@" would otherwise split them.
_LOOKALIKES = {
    # Greek lookalikes
    "α": "a", "Α": "a", "β": "b", "Β": "b", "ε": "e", "Ε": "e",
    "η": "h", "Η": "h", "ι": "i", "Ι": "i", "κ": "k", "Κ": "k",
    "μ": "m", "Μ": "m", "ν": "n", "Ν": "n", "ο": "o", "Ο": "o",
    "ρ": "p", "Ρ": "p", "τ": "t", "Τ": "t", "υ": "y", "Υ": "y",
    "χ": "x", "Χ": "x", "ζ": "z", "Ζ": "z",
    # Cyrillic lookalikes
    "а": "a", "А": "a", "е": "e", "Е": "e", "к": "k", "К": "k",
    "м": "m", "М": "m", "н": "h", "Н": "h", "о": "o", "О": "o",
    "р": "p", "Р": "p", "с": "c", "С": "c", "т": "t", "Т": "t",
    "у": "y", "У": "y", "х": "x", "Х": "x", "ѕ": "s", "Ѕ": "s",
    # Symbols
    "$": "s", "@": "a",
}

# Folded per word, after number-like suffixes ("slot88") are stripped.
_LEET_DIGITS = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"}

_WORD_SPLIT_RE = re.compile(r"[\W_]+", re.UNICODE)
_EDGE_DIGITS_RE = re.compile(r"^\d{2,}|\d{2,}$")
_REPEATED_CHAR_RE = re.compile(r"(.)\1+")


def words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(_LOOKALIKES.get(c, c) for c in text if c not in _ZERO_WIDTH)

    tokens: list[str] = []
    for raw in _WORD_SPLIT_RE.split(text):
        raw = _EDGE_DIGITS_RE.sub("", raw)
        if not raw or raw.isdigit():
            continue
        token = "".join(_LEET_DIGITS.get(c, c) for c in raw).lower()
        tokens.append(_REPEATED_CHAR_RE.sub(r"\1", token))
    return _merge_spelled_out_letters(tokens)


def _merge_spelled_out_letters(tokens: list[str]) -> list[str]:
    """Rejoin "s l o t" / "s.l.o.t" into "slot"."""
    merged: list[str] = []
    run = ""
    for token in tokens + [""]:
        if len(token) == 1:
            run += token
            continue
        if run:
            merged.append(_REPEATED_CHAR_RE.sub(r"\1", run))
            run = ""
        if token:
            merged.append(token)
    return merged
