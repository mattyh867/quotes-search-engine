# Testing Strategy

This document explains the approach taken to testing the search tool -
what's tested, why, how to run it, and what's not covered.

## Approach

Tests are organised into four files, each focused on a single module:

- `test_crawler.py` - the crawler (link extraction, fetching, the crawl loop)
- `test_indexer.py` - tokenisation, the inverted index, and persistence
- `test_search.py` - the `find` and `print_word` functions
- `test_integration.py` - end-to-end tests wiring the real components together

The split between unit and integration tests is deliberate. Unit tests mock
their dependencies and assert on isolated behaviour, which makes failures
easy to localise. Integration tests use the real crawler, indexer, and
search code together (only the network is mocked), which proves the system
works as a whole; bugs in how the pieces fit together don't always show
up in unit tests.

## Why we mock the network

The target site (`quotes.toscrape.com`) is a real third-party service. Tests
that hit it would be:

- **Slow** - the politeness window alone is 6 seconds per page, so even a
  small crawl would take half a minute per test run.
- **Flaky** - network failures, rate limiting, or the site going down would
  cause unrelated test failures.
- **Rude** - running the full test suite repeatedly during development
  would hammer a site that exists for educational scraping, not load testing.

Instead, `requests.get` and `crawler.fetch_page` are patched to return
canned HTML for known URLs. `time.sleep` is also patched so the politeness
delay doesn't slow tests down — but assertions still verify it would have
been called with the right value in production.

## Edge cases covered

The rubric specifically asks for edge cases. Below is what's been tested
and where:

| Edge case | Test file | Test name |
|---|---|---|
| Empty input string | `test_indexer.py` | `test_tokenise_empty_string` |
| Whitespace-only input | `test_indexer.py` | `test_tokenise_whitespace_only` |
| Punctuation-only input | `test_indexer.py` | `test_tokenise_punctuation_only` |
| Unicode / accented chars | `test_indexer.py` | `test_tokenise_drops_accented_characters` |
| Empty page text | `test_indexer.py` | `test_add_page_with_empty_text_adds_nothing` |
| Missing index file | `test_indexer.py` | `test_load_missing_file_raises_filenotfound` |
| Malformed JSON | `test_indexer.py` | `test_load_malformed_json_raises` |
| Malformed HTML | `test_crawler.py` | `test_extract_links_handles_malformed_html` |
| Page with no links | `test_crawler.py` | `test_extract_links_returns_empty_for_no_anchors` |
| Network failure mid-crawl | `test_crawler.py` | `test_crawl_continues_when_a_fetch_fails` |
| External domains | `test_crawler.py` | `test_crawl_stays_on_allowed_domain` |
| Duplicate URLs (loops) | `test_crawler.py` | `test_crawl_does_not_revisit_seen_urls` |
| URL variants (`/page/1/`) | `test_crawler.py` | `test_normalise_prevents_duplicate_page_one_crawls` |
| Empty query | `test_search.py` | `test_find_empty_query_returns_empty` |
| Punctuation-only query | `test_search.py` | `test_find_punctuation_only_query_returns_empty` |
| Word not in index | `test_search.py` | `test_find_missing_word_returns_empty` |
| Mixed-case query | `test_search.py` | `test_find_is_case_insensitive` |
| Punctuation in query | `test_search.py` | `test_find_strips_punctuation` |
| Apostrophe words (e.g. "don't") | `test_search.py` | `test_find_splits_apostrophe_words` |
| One missing word in multi-word query | `test_search.py` | `test_find_multi_word_one_missing_returns_empty` |

## What we deliberately don't test

A few things were considered and consciously left out:

- **The argparse CLI layer in `main.py`.** The handlers are thin wrappers
  that delegate to already-tested functions; testing argparse itself is
  testing the standard library. The cost of mocking `sys.argv` and
  capturing exits outweighed the marginal coverage gain.
- **Performance.** The brief specifies correctness, not throughput. A
  performance test would be flaky (depends on the runner's speed) and
  doesn't earn any rubric marks.
- **The `if __name__ == "__main__":` blocks** in `crawler.py` and
  `indexer.py`. These exist for ad-hoc manual testing during development;
  they're not part of the public interface.

These gaps are visible in the coverage report below.

## Running the tests

From the project root:

```bash
pytest -v
```

To see coverage:

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

## Tools used

- **pytest** as the test runner — chosen over `unittest` for its concise
  assertion style and built-in fixtures (`tmp_path`, `capsys`).
- **unittest.mock** (standard library) for patching `requests.get` and
  `time.sleep` in crawler tests.
- **pytest-cov** for line coverage reporting.