from unittest.mock import patch, MagicMock

import pytest

import main
from main import (
    _load_or_exit,
    cmd_build,
    cmd_load,
    cmd_print,
    cmd_find,
    build_parser,
)


# _load_or_exit

def test_load_or_exit_returns_index_when_file_exists():
    fake_index = {"hello": {"http://example.com/": {"freq": 1, "positions": [0]}}}
    with patch("main.load_index", return_value=fake_index):
        result = _load_or_exit("anywhere.json")
    assert result == fake_index


def test_load_or_exit_exits_when_file_missing(capsys):
    with patch("main.load_index", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as exc_info:
            _load_or_exit("missing.json")

    # exit code should be non-zero
    assert exc_info.value.code != 0

    out = capsys.readouterr().out
    assert "missing.json" in out
    assert "build" in out.lower()


# argparse wiring

def test_parser_requires_a_subcommand():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_accepts_all_four_commands():
    parser = build_parser()
    # if any of these raise, argparse rejected the command
    parser.parse_args(["build"])
    parser.parse_args(["load"])
    parser.parse_args(["print", "hello"])
    parser.parse_args(["find", "hello"])


def test_parser_find_accepts_multiple_words():
    parser = build_parser()
    args = parser.parse_args(["find", "good", "friends", "forever"])
    assert args.query == ["good", "friends", "forever"]


def test_parser_find_requires_at_least_one_word():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["find"])


def test_parser_print_requires_a_word():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["print"])


# cmd_build

def test_cmd_build_calls_crawl_and_save(capsys):
    fake_index = {"hi": {}}
    args = MagicMock(seed="https://example.com/", output="out.json", max_pages=5)

    with patch("main.crawl", return_value=fake_index) as mock_crawl, \
         patch("main.save_index") as mock_save:
        cmd_build(args)

    mock_crawl.assert_called_once_with(seed="https://example.com/", max_pages=5)
    mock_save.assert_called_once_with(fake_index, "out.json")

    out = capsys.readouterr().out
    assert "Crawling" in out
    assert "out.json" in out


# cmd_load

def test_cmd_load_prints_stats(capsys):
    fake_index = {
        "hello": {"http://a/": {}, "http://b/": {}},
        "world": {"http://a/": {}},
    }
    args = MagicMock(input="some.json")

    with patch("main.load_index", return_value=fake_index):
        cmd_load(args)

    out = capsys.readouterr().out
    assert "2 unique terms" in out
    assert "3 term-document postings" in out  # 2 + 1


def test_cmd_load_exits_on_missing_file():
    args = MagicMock(input="nope.json")
    with patch("main.load_index", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit):
            cmd_load(args)


# cmd_print

def test_cmd_print_delegates_to_print_word():
    args = MagicMock(input="i.json", word="hello")
    fake_index = {"hello": {}}

    with patch("main.load_index", return_value=fake_index), \
         patch("main.print_word") as mock_print_word:
        cmd_print(args)

    mock_print_word.assert_called_once_with(fake_index, "hello")


# cmd_find

def test_cmd_find_prints_matching_pages(capsys):
    args = MagicMock(input="i.json", query=["good"])
    fake_index = {"good": {}}

    with patch("main.load_index", return_value=fake_index), \
         patch("main.find", return_value=(["http://a/", "http://b/"], ["good"])):
        cmd_find(args)

    out = capsys.readouterr().out
    assert "2 page(s) found" in out
    assert "http://a/" in out
    assert "http://b/" in out


def test_cmd_find_handles_no_results(capsys):
    args = MagicMock(input="i.json", query=["zzznotaword"])

    with patch("main.load_index", return_value={}), \
         patch("main.find", return_value=([], ["zzznotaword"])):
        cmd_find(args)

    out = capsys.readouterr().out
    assert "No matching pages" in out


def test_cmd_find_surfaces_normalised_query(capsys):
    """When the query gets cleaned up, the user should see what was actually searched."""
    args = MagicMock(input="i.json", query=["GOOD!"])

    with patch("main.load_index", return_value={}), \
         patch("main.find", return_value=(["http://a/"], ["good"])):
        cmd_find(args)

    out = capsys.readouterr().out
    assert "searching for: good" in out


def test_cmd_find_stays_quiet_when_query_unchanged(capsys):
    """If the query didn't need normalising, no notice should appear."""
    args = MagicMock(input="i.json", query=["good"])

    with patch("main.load_index", return_value={}), \
         patch("main.find", return_value=(["http://a/"], ["good"])):
        cmd_find(args)

    out = capsys.readouterr().out
    assert "searching for:" not in out


# main() entry point

def test_main_dispatches_to_correct_handler():
    """A test that argparse + dispatch wiring works end-to-end."""
    with patch("sys.argv", ["main.py", "load", "--input", "x.json"]), \
         patch("main.load_index", return_value={}):
        main.main()  # should not raise