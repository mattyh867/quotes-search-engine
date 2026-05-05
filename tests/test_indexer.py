import json

import pytest

import indexer
from indexer import (
    tokenise,
    make_index,
    add_page,
    save_index,
    load_index,
)


# tokenise

def test_tokenise_basic_split():
    assert tokenise("the quick brown fox") == ["the", "quick", "brown", "fox"]


def test_tokenise_lowercases():
    assert tokenise("The Quick BROWN Fox") == ["the", "quick", "brown", "fox"]


def test_tokenise_strips_punctuation():
    assert tokenise("Hello, world! How's it going?") == \
        ["hello", "world", "how", "s", "it", "going"]


def test_tokenise_keeps_numbers():
    assert tokenise("year 2026 is here") == ["year", "2026", "is", "here"]


def test_tokenise_empty_string():
    assert tokenise("") == []


def test_tokenise_whitespace_only():
    assert tokenise("   \t\n  ") == []


def test_tokenise_punctuation_only():
    assert tokenise("!!! ??? ...") == []


def test_tokenise_drops_accented_characters():
    # The current regex only keeps a-z0-9 — accented chars become separators.
    # This test pins down that behaviour so we notice if it changes.
    assert tokenise("café résumé") == ["caf", "r", "sum"]


def test_tokenise_handles_runs_of_separators():
    assert tokenise("foo!!!---bar") == ["foo", "bar"]


# add_page

def test_add_page_records_frequency():
    index = make_index()
    add_page(index, "http://example.com/a", "the cat and the dog and the bird")
    assert index["the"]["http://example.com/a"]["freq"] == 3
    assert index["and"]["http://example.com/a"]["freq"] == 2
    assert index["cat"]["http://example.com/a"]["freq"] == 1


def test_add_page_records_positions():
    index = make_index()
    add_page(index, "http://example.com/a", "alpha beta alpha gamma alpha")
    # alpha appears at token positions 0, 2, 4
    assert index["alpha"]["http://example.com/a"]["positions"] == [0, 2, 4]
    assert index["beta"]["http://example.com/a"]["positions"] == [1]


def test_add_page_positions_are_sequential_and_zero_indexed():
    index = make_index()
    add_page(index, "http://example.com/a", "one two three")
    assert index["one"]["http://example.com/a"]["positions"] == [0]
    assert index["two"]["http://example.com/a"]["positions"] == [1]
    assert index["three"]["http://example.com/a"]["positions"] == [2]


def test_add_page_handles_multiple_pages():
    index = make_index()
    add_page(index, "http://example.com/a", "shared word here")
    add_page(index, "http://example.com/b", "shared again")

    postings = index["shared"]
    assert set(postings.keys()) == {"http://example.com/a", "http://example.com/b"}
    assert postings["http://example.com/a"]["freq"] == 1
    assert postings["http://example.com/b"]["freq"] == 1


def test_add_page_with_empty_text_adds_nothing():
    index = make_index()
    add_page(index, "http://example.com/a", "")
    assert len(index) == 0


def test_add_page_is_case_insensitive():
    index = make_index()
    add_page(index, "http://example.com/a", "Apple APPLE apple")
    assert index["apple"]["http://example.com/a"]["freq"] == 3
    assert "Apple" not in index
    assert "APPLE" not in index


# save_index / load_index

def test_save_and_load_round_trip(tmp_path):
    index = make_index()
    add_page(index, "http://example.com/a", "hello world")

    path = tmp_path / "index.json"
    save_index(index, str(path))
    loaded = load_index(str(path))

    assert loaded["hello"]["http://example.com/a"]["freq"] == 1
    assert loaded["world"]["http://example.com/a"]["positions"] == [1]


def test_save_creates_parent_directories(tmp_path):
    index = make_index()
    add_page(index, "http://example.com/a", "hi")

    path = tmp_path / "nested" / "deeper" / "index.json"
    save_index(index, str(path))

    assert path.exists()


def test_save_writes_valid_json(tmp_path):
    """The file should be readable as plain JSON, not a pickled defaultdict."""
    index = make_index()
    add_page(index, "http://example.com/a", "hello")

    path = tmp_path / "index.json"
    save_index(index, str(path))

    with open(path) as f:
        raw = json.load(f)

    assert isinstance(raw, dict)
    assert isinstance(raw["hello"], dict)


def test_load_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_index(str(tmp_path / "nope.json"))


def test_load_malformed_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("this is not json {{{")

    with pytest.raises(json.JSONDecodeError):
        load_index(str(path))


# integration

def test_full_pipeline(tmp_path):
    """tokenise -> add_page -> save -> load should preserve everything."""
    index = make_index()
    add_page(index, "http://example.com/a", "The quick brown fox")
    add_page(index, "http://example.com/b", "The lazy dog")

    path = tmp_path / "index.json"
    save_index(index, str(path))
    loaded = load_index(str(path))

    # the term "the" appears in both pages
    assert set(loaded["the"].keys()) == {
        "http://example.com/a", "http://example.com/b"
    }
    # each page-specific term only appears in its page
    assert set(loaded["fox"].keys()) == {"http://example.com/a"}
    assert set(loaded["dog"].keys()) == {"http://example.com/b"}