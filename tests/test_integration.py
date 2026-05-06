from unittest.mock import patch

import pytest

import crawler
from crawler import crawl
from indexer import save_index, load_index
from search import find, print_word


# A tiny fake site. Three pages, with a couple of shared words so we can
# test multi-page postings and intersection queries.
FAKE_SITE = {
    "https://quotes.toscrape.com/": """
        <html><body>
          <p>The best quotes about love and friendship.</p>
          <a href="/page/2/">next</a>
          <a href="/author/einstein">einstein</a>
        </body></html>
    """,
    "https://quotes.toscrape.com/page/2/": """
        <html><body>
          <p>More quotes about love and life.</p>
          <a href="/author/einstein">einstein</a>
        </body></html>
    """,
    "https://quotes.toscrape.com/author/einstein": """
        <html><body>
          <p>Albert Einstein. Famous for life and science.</p>
        </body></html>
    """,
}


@pytest.fixture
def crawled_index():
    """Crawl the fake site once and hand the index to the test."""
    def fake_fetch(url):
        return FAKE_SITE.get(url)

    with patch("crawler.fetch_page", side_effect=fake_fetch), \
         patch("crawler.time.sleep"):
        return crawl(seed="https://quotes.toscrape.com/", max_pages=10)


# crawl + index

def test_crawl_indexes_all_three_pages(crawled_index):
    """Every page should be reachable from the seed and appear in the index."""
    indexed_urls = set()
    for postings in crawled_index.values():
        indexed_urls.update(postings.keys())

    assert indexed_urls == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/author/einstein",
    }


def test_crawl_produces_expected_terms(crawled_index):
    """Words from the page text should show up as index keys."""
    for word in ["love", "life", "einstein", "quotes"]:
        assert word in crawled_index, f"expected '{word}' in index"


def test_shared_word_appears_in_multiple_pages(crawled_index):
    """'love' is on the seed and page 2 — its postings should reflect that."""
    love_postings = crawled_index["love"]
    assert "https://quotes.toscrape.com/" in love_postings
    assert "https://quotes.toscrape.com/page/2/" in love_postings


# crawl + index + save + load

def test_full_pipeline_round_trip(tmp_path, crawled_index):
    """Crawl → save → load → search. The whole flow end to end."""
    path = tmp_path / "index.json"
    save_index(crawled_index, str(path))
    loaded = load_index(str(path))

    # search the loaded index, not the in-memory one
    results, _ = find(loaded, ["love"])
    assert "https://quotes.toscrape.com/" in results
    assert "https://quotes.toscrape.com/page/2/" in results


# search against the real crawled index

def test_search_single_word(crawled_index):
    results, _ = find(crawled_index, ["einstein"])
    # einstein appears on the author page and is mentioned on the linking pages
    assert "https://quotes.toscrape.com/author/einstein" in results


def test_search_multi_word_intersection(crawled_index):
    """'love' and 'life' both appear on page 2 — that page should be in results."""
    results, _ = find(crawled_index, ["love", "life"])
    assert "https://quotes.toscrape.com/page/2/" in results
    # the einstein page has 'life' but not 'love' — must be excluded
    assert "https://quotes.toscrape.com/author/einstein" not in results


def test_search_word_not_on_site_returns_empty(crawled_index):
    results, _ = find(crawled_index, ["zzznotaword"])
    assert results == []


def test_print_word_against_real_index(crawled_index, capsys):
    print_word(crawled_index, "love")
    out = capsys.readouterr().out

    # the URLs should appear, and we should see "page(s)" wording
    assert "page" in out.lower()
    assert "https://quotes.toscrape.com" in out


# politeness, end to end

def test_full_crawl_respects_politeness_window():
    """Even at the integration level, no real call should sleep less than 6s."""
    def fake_fetch(url):
        return FAKE_SITE.get(url)

    with patch("crawler.fetch_page", side_effect=fake_fetch), \
         patch("crawler.time.sleep") as mock_sleep:
        crawl(seed="https://quotes.toscrape.com/", max_pages=10)

    assert mock_sleep.called
    for call in mock_sleep.call_args_list:
        assert call.args[0] >= crawler.POLITENESS_DELAY