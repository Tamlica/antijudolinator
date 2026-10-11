from app.classifier.normalize import words


def test_lowercases_plain_text():
    assert words("SLOT") == ["slot"]


def test_folds_greek_lookalikes():
    # Greek omicron (ο, U+03BF) instead of Latin o
    assert words("slοt") == ["slot"]


def test_folds_cyrillic_lookalikes():
    # Cyrillic dze (ѕ, U+0455) and o (о, U+043E) instead of Latin s, o
    assert words("ѕlоt") == ["slot"]


def test_folds_leetspeak_digits_and_symbols():
    assert words("sl0t g4c0r $pin") == ["slot", "gacor", "spin"]


def test_rejoins_spelled_out_letters():
    assert words("s.l.o.t") == ["slot"]
    assert words("main s l o t yuk") == ["main", "slot", "yuk"]
    assert words("s_l_o_t") == ["slot"]


def test_strips_zero_width_characters():
    assert words("sl​ot") == ["slot"]


def test_collapses_repeated_characters():
    assert words("slooot") == ["slot"]


def test_strips_number_suffixes_and_drops_plain_numbers():
    assert words("slot88 gacor777 kasih 100 ribu") == ["slot", "gacor", "kasih", "ribu"]


def test_words_splits_on_whitespace_and_punctuation():
    assert words("halo, main sl0t yuk!") == ["halo", "main", "slot", "yuk"]
