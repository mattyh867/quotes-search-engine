import pytest

from search import find, print_word


def _sample_index():
    return {
        "good": {
            "http://example.com/a": {"freq": 3, "positions": [1, 5, 10]},
            "http://example.com/b": {"freq": 1, "positions": [4]},
            "http://example.com/c": {"freq": 2, "positions": [0, 7]},
        },
        "friends": {
            "http://example.com/a": {"freq": 1, "positions": [2]},
            "http://example.com/c": {"freq": 1, "positions": [8]},
        },
        "love": {
            "http://example.com/b": {"freq": 5, "positions": [0, 3, 6, 9, 12]},
        },
        "world": {
            "http://example.com/d": {"freq": 1, "positions": [0]},
        },
    }


# find: single word

def test_find_single_word_returns_all_pages():
    index = _sample_index()
    results, _ = find(index, ["good"])
    assert set(results) == {
        "http://example.com/a",
        "http://example.com/b",
        "http://example.com/c",
    }


def test_find_single_word_ranked_by_frequency():
    index = _sample_index()
    results, _ = find(index, ["good"])
    # /a has freq 3, /c has 2, /b has 1 — should come back in that order
    assert results == [
        "http://example.com/a",
        "http://example.com/c",
        "http://example.com/b",
    ]


def test_find_missing_word_returns_empty():
    index = _sample_index()
    results, _ = find(index, ["nonexistent"])
    assert results == []


# find: multi-word

def test_find_multi_word_returns_intersection_not_union():
    """Make sure we're intersecting, not unioning."""
    index = _sample_index()
    results, _ = find(index, ["good", "friends"])
    # /a and /c have both words; /b has only "good"
    assert set(results) == {"http://example.com/a", "http://example.com/c"}
    assert "http://example.com/b" not in results


def test_find_multi_word_ranked_by_if_idf():
    index = _sample_index()
    results, _ = find(index, ["good", "friends"])
    # /a has higher tf for "good" (3 vs 2), and both pages tie on
    # "friends" (1 each). TF-IDF preserves that ordering.
    assert results == ["http://example.com/a", "http://example.com/c"]


def test_find_multi_word_one_missing_returns_empty():
    """If any query word is absent, the intersection must be empty."""
    index = _sample_index()
    results, _ = find(index, ["good", "nonexistent"])
    assert results == []


# find: input normalisation

def test_find_is_case_insensitive():
    index = _sample_index()
    lower, _ = find(index, ["good"])
    upper, _ = find(index, ["GOOD"])
    mixed, _ = find(index, ["Good"])
    assert lower == upper == mixed


def test_find_strips_punctuation():
    index = _sample_index()
    plain, _ = find(index, ["good"])
    punct, _ = find(index, ["good!"])
    assert plain == punct


def test_find_splits_apostrophe_words():
    """'don't' becomes ['don', 't'] via the tokeniser — both must match."""
    index = {
        "don": {"http://example.com/a": {"freq": 1, "positions": [0]}},
        "t": {"http://example.com/a": {"freq": 1, "positions": [1]}},
    }
    results, normalised = find(index, ["don't"])
    assert results == ["http://example.com/a"]
    assert normalised == ["don", "t"]


def test_find_empty_query_returns_empty():
    index = _sample_index()
    results, _ = find(index, [])
    assert results == []


def test_find_punctuation_only_query_returns_empty():
    index = _sample_index()
    results, _ = find(index, ["!!!", "???"])
    assert results == []


def test_find_returns_normalised_query_for_caller():
    index = _sample_index()
    _, normalised = find(index, ["GOOD!", "Friends"])
    assert normalised == ["good", "friends"]


# print_word

def test_print_word_known_word_shows_stats(capsys):
    index = _sample_index()
    print_word(index, "good")
    out = capsys.readouterr().out

    # total of freqs across pages: 3 + 1 + 2 = 6
    assert "6" in out
    assert "3 page" in out  # "3 page(s)"
    # all three URLs should appear
    assert "http://example.com/a" in out
    assert "http://example.com/b" in out
    assert "http://example.com/c" in out


def test_print_word_missing_word_says_not_found(capsys):
    index = _sample_index()
    print_word(index, "nonexistent")
    out = capsys.readouterr().out
    assert "not found" in out.lower()


def test_print_word_is_case_insensitive(capsys):
    index = _sample_index()
    print_word(index, "GOOD")
    out_upper = capsys.readouterr().out

    print_word(index, "good")
    out_lower = capsys.readouterr().out

    assert out_upper == out_lower


def test_print_word_strips_punctuation(capsys):
    index = _sample_index()
    print_word(index, "good!")
    out = capsys.readouterr().out
    # should resolve to "good" and find it
    assert "not found" not in out.lower()
    assert "http://example.com/a" in out


def test_print_word_punctuation_only_handled_gracefully(capsys):
    index = _sample_index()
    print_word(index, "!!!")
    out = capsys.readouterr().out
    # whatever the message, it shouldn't crash and shouldn't claim to find anything
    assert "http://example.com" not in out


def test_find_ranks_rare_term_higher_than_common_term():
    """TF-IDF should beat raw frequency: pages where the rare query
    term dominates rank above pages where the common term dominates,
    even if the latter has more total matches.
    """
    from indexer import make_index, add_page

    idx = make_index()

    # 'rare' appears in only 2 docs out of 10 = high IDF.
    # 'common' appears in all 10 → IDF = log(10/10) = 0.
    add_page(idx, "url_a", "rare " + "common " * 100)   # rare ×1, common ×100
    add_page(idx, "url_b", "rare " * 5 + "common")      # rare ×5, common ×1
    for i in range(8):
        add_page(idx, f"url_filler_{i}", "common")

    results, _ = find(idx, ["rare", "common"])

    # Both A and B match. With raw frequency A wins (101 vs 6).
    # With TF-IDF B wins because rare has all the IDF weight.
    assert results == ["url_b", "url_a"]