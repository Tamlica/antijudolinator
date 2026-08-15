from app.classifier.learn import extract_candidate_patterns


def test_extracts_distinctive_tokens_dropping_stopwords():
    assert extract_candidate_patterns("makasih kak main sl0t gacor yuk") == [
        "main",
        "slot",
        "gacor",
        "yuk",
    ]


def test_drops_short_tokens_and_duplicates():
    assert extract_candidate_patterns("wa wa wa daftar di sini ya") == ["daftar", "sini"]


def test_returns_empty_list_when_only_stopwords():
    assert extract_candidate_patterns("terima kasih kak semoga selalu") == []
