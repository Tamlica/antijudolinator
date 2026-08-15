from app.classifier.match import find_match


def test_finds_exact_substring_match():
    assert find_match("halojudigacor123", ["gacor"]) == "gacor"


def test_returns_none_when_no_pattern_matches():
    assert find_match("halo semua terima kasih atas dukungannya", ["gacor"]) is None


def test_finds_match_within_one_edit_of_pattern():
    # "gakor" is one substitution away from "gacor"
    assert find_match("halojudigakor123", ["gacor"]) == "gacor"


def test_does_not_fuzzy_match_short_patterns():
    # short patterns (<4 chars) must match exactly, to avoid false positives
    assert find_match("halo bos", ["cs"]) is None


def test_returns_first_matching_pattern_in_list():
    assert find_match("promo toto hari ini", ["toto", "slot"]) == "toto"
