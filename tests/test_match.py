import pytest

from app.classifier.match import find_match
from app.classifier.normalize import words
from app.classifier.seed_patterns import SEED_PATTERNS

SEEDS = sorted(SEED_PATTERNS, key=len, reverse=True)


def test_finds_pattern_inside_a_word():
    assert find_match(words("halojudigacor123"), ["gacor"]) == "gacor"


def test_returns_none_when_no_pattern_matches():
    assert find_match(words("halo semua terima kasih atas dukungannya"), ["gacor"]) is None


def test_finds_match_within_one_edit_of_pattern():
    # "gakor" is one substitution away from "gacor"
    assert find_match(words("halojudigakor123"), ["gacor"]) == "gacor"


def test_returns_first_matching_pattern_in_list():
    assert find_match(words("promo toto hari ini"), ["toto", "slot"]) == "toto"


def test_does_not_match_across_word_boundaries():
    assert find_match(words("smart people"), ["rtp"]) is None


@pytest.mark.parametrize(
    "message",
    [
        "Kirim foto kucing dong kak",
        "Mantap bang, motornya keren",
        "smart people watch this",
        "Gas terus pilot!",
        "Plot twist banget episode ini",
        "spot nonton favorit",
        "Semangat terus, mainnya jago",
        "100 ribu buat jajan",
        "Salam dari Jakarta, sehat selalu bang",
        "otomatis subscribe, mantap kontennya",
        "slow down bro, santai aja",
    ],
)
def test_normal_donations_are_never_flagged_by_seed_patterns(message):
    assert find_match(words(message), SEEDS) is None


@pytest.mark.parametrize(
    "message",
    [
        "promo sl0t gacor daftar sekarang",
        "S L O T G A C O R hari ini",
        "situs slot88 maxwin",
        "main di slotgacor777 bos",
        "sl ot terpercaya",
        "j4ckp0t terus",
        "rtp live tinggi",
        "spin gratis tiap hari",
        "ѕlоt online",
    ],
)
def test_gambling_promos_are_flagged_by_seed_patterns(message):
    assert find_match(words(message), SEEDS) is not None
