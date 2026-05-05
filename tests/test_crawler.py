from unittest.mock import patch, MagicMock

import pytest
import requests

import crawler
from crawler import normalise, extract_links, fetch_page, crawl


# normalise

def test_normalise_strips_page_one():
    assert normalise("https://quotes.toscrape.com/tag/love/page/1/") == \
        "https://quotes.toscrape.com/tag/love/"


def test_normalise_leaves_other_urls_alone():
    url = "https://quotes.toscrape.com/tag/love/page/2/"
    assert normalise(url) == url


# extract_links

SAMPLE_HTML = """
<html><body>
  <a href="/page/2/">Next</a>
  <a href="https://quotes.toscrape.com/author/Einstein">Einstein</a>
  <a href="https://twitter.com/somebody">External</a>
  <a href="/login">Login</a>
  <a href="/tag/love/#top">Love</a>
</body></html>
"""


def test_extract_links_resolves_relative_urls():
    links = extract_links(SAMPLE_HTML, "https://quotes.toscrape.com/", "quotes.toscrape.com")
    assert "https://quotes.toscrape.com/page/2/" in links


def test_extract_links_filters_external_domains():
    links = extract_links(SAMPLE_HTML, "https://quotes.toscrape.com/", "quotes.toscrape.com")
    assert not any("twitter.com" in url for url in links)


def test_extract_links_skips_login_logout():
    links = extract_links(SAMPLE_HTML, "https://quotes.toscrape.com/", "quotes.toscrape.com")
    assert not any(url.rstrip("/").endswith("/login") for url in links)


def test_extract_links_strips_fragments():
    links = extract_links(SAMPLE_HTML, "https://quotes.toscrape.com/", "quotes.toscrape.com")
    assert "https://quotes.toscrape.com/tag/love/" in links
    assert not any("#" in url for url in links)


# fetch_page

def test_fetch_page_returns_text_on_success():
    fake_response = MagicMock()
    fake_response.text = "<html>hello</html>"
    fake_response.raise_for_status = MagicMock()

    with patch("crawler.requests.get", return_value=fake_response):
        assert fetch_page("https://example.com") == "<html>hello</html>"


def test_fetch_page_returns_none_on_http_error():
    with patch("crawler.requests.get", side_effect=requests.ConnectionError("boom")):
        assert fetch_page("https://example.com") is None


# crawl

def _html_with_links(*paths):
    """Helper to build pages that link to each other."""
    anchors = "".join(f'<a href="{p}">link</a>' for p in paths)
    return f"<html><body>{anchors}</body></html>"


def test_crawl_respects_max_pages():
    pages = {
        "https://quotes.toscrape.com/": _html_with_links("/a", "/b", "/c"),
        "https://quotes.toscrape.com/a": _html_with_links("/d"),
        "https://quotes.toscrape.com/b": _html_with_links("/e"),
        "https://quotes.toscrape.com/c": _html_with_links("/f"),
    }

    def fake_fetch(url):
        return pages.get(url, "<html></html>")

    with patch("crawler.fetch_page", side_effect=fake_fetch), \
         patch("crawler.time.sleep"):  # don't actually wait for testing purposes
        index = crawl(max_pages=2)

    # we asked for 2, we should have indexed exactly 2 unique URLs
    indexed_urls = set()
    for postings in index.values():
        indexed_urls.update(postings.keys())
    assert len(indexed_urls) == 2


def test_crawl_does_not_revisit_seen_urls():
    # Page A links back to the seed, which would loop forever if we didn't keep track of seen URLs
    pages = {
        "https://quotes.toscrape.com/": _html_with_links("/a"),
        "https://quotes.toscrape.com/a": _html_with_links("/", "/a"),
    }

    fetch_calls = []

    def fake_fetch(url):
        fetch_calls.append(url)
        return pages.get(url, "<html></html>")

    with patch("crawler.fetch_page", side_effect=fake_fetch), \
         patch("crawler.time.sleep"):
        crawl(max_pages=10)

    assert len(fetch_calls) == len(set(fetch_calls))


def test_crawl_respects_politeness_delay():
    pages = {
        "https://quotes.toscrape.com/": _html_with_links("/a"),
        "https://quotes.toscrape.com/a": "<html></html>",
    }

    with patch("crawler.fetch_page", side_effect=lambda u: pages.get(u, "")), \
         patch("crawler.time.sleep") as mock_sleep:
        crawl(max_pages=2)

    # every sleep call should be at least the politeness delay
    assert mock_sleep.called
    for call in mock_sleep.call_args_list:
        delay = call.args[0]
        assert delay >= crawler.POLITENESS_DELAY