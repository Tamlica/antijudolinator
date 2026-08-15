from app.classifier.normalize import normalize, words


def test_lowercases_plain_text():
    assert normalize("SLOT") == "slot"


def test_folds_greek_lookalikes():
    # Greek omicron (ο, U+03BF) instead of Latin o
    assert normalize("slοt") == "slot"


def test_folds_cyrillic_lookalikes():
    # Cyrillic dze (ѕ, U+0455) and o (о, U+043E) instead of Latin s, o
    assert normalize("ѕlоt") == "slot"


def test_folds_leetspeak_digits():
    assert normalize("sl0t") == "slot"


def test_strips_separators_between_letters():
    assert normalize("s.l.o.t") == "slot"


def test_strips_zero_width_characters():
    assert normalize("sl​ot") == "slot"


def test_collapses_repeated_characters():
    assert normalize("slooot") == "slot"


def test_words_splits_on_whitespace_and_punctuation():
    assert words("halo, main sl0t yuk!") == ["halo", "main", "slot", "yuk"]


def test_words_folds_confusables_per_token():
    assert words("promo slοt gacor") == ["promo", "slot", "gacor"]
