"""Normalize text so obfuscated gambling-promo messages fold to a matchable form."""

import re
import unicodedata

_ZERO_WIDTH = {"​", "‌", "‍", "﻿"}

_CONFUSABLES = {
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
    # Leetspeak digits/symbols
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "8": "b", "$": "s", "@": "a",
}

_SEPARATORS_RE = re.compile(r"[\s\.\-_,;:'\"`~^*+=/\\]+")
_WORD_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)
_REPEATED_CHAR_RE = re.compile(r"(.)\1+")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if c not in _ZERO_WIDTH)
    text = "".join(_CONFUSABLES.get(c, c) for c in text)
    return text.lower()


def normalize(text: str) -> str:
    text = _fold(text)
    text = _SEPARATORS_RE.sub("", text)
    text = _REPEATED_CHAR_RE.sub(r"\1", text)
    return text


def words(text: str) -> list[str]:
    text = _fold(text)
    tokens = [t for t in _WORD_SPLIT_RE.split(text) if t]
    return [_REPEATED_CHAR_RE.sub(r"\1", t) for t in tokens]
