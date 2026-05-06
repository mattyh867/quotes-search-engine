"""
Web crawler for the search tool.
 
Does a breadth-first crawl of quotes.toscrape.com starting from a seed
URL and feeds each page's text into the inverted index as it goes, with a 6
second politeness delay between requests.
"""

import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from indexer import add_page, make_index


SEED_URL = "https://quotes.toscrape.com/"
POLITENESS_DELAY = 6
REQUEST_TIMEOUT = 15
USER_AGENT = "COMP3011-Crawler/0.1"
SKIP_SUFFIXES = ("/login", "/logout") # Pages we don't want to follow


def fetch_page(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"! error fetching {url}: {e}")
        return None


def normalise(url):
    """Collapse trivially equivalent URL variants."""
    # /tag/foo/page/1/ is the same content as /tag/foo/
    if url.endswith("/page/1/"):
        url = url[: -len("page/1/")]
    return url


def extract_links(html, base_url, allowed_domain):
    soup = BeautifulSoup(html, "html.parser")
    found = set()

    for tag in soup.find_all("a", href=True):
        url = urljoin(base_url, tag["href"]).split("#", 1)[0]
        url = normalise(url)

        if urlparse(url).netloc != allowed_domain:
            continue
        if any(url.rstrip("/").endswith(s) for s in SKIP_SUFFIXES):
            continue

        found.add(url)

    return found


def crawl(seed=SEED_URL, max_pages=None):
    index = make_index()
    allowed_domain = urlparse(seed).netloc
    queue = [seed]
    seen = set()

    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        html = fetch_page(url)
        if html is None:
            time.sleep(POLITENESS_DELAY)
            continue

        # Index the page text
        try:
            soup = BeautifulSoup(html, "html.parser")
            add_page(index, url, soup.get_text(separator=" "))
        except Exception as e:
            print(f"! index error on {url}: {e}")

        # Queue up any new links
        for link in extract_links(html, url, allowed_domain):
            if any(link.rstrip("/").endswith(s.rstrip("/")) for s in SKIP_SUFFIXES):
              continue
            if link not in seen:
                queue.append(link)

        print(f"[{len(seen)}] indexed {url}")

        if max_pages and len(seen) >= max_pages:
            break

        time.sleep(POLITENESS_DELAY)

    return index


if __name__ == "__main__":
    idx = crawl(max_pages=5)
    print(f"\nFinished. {len(idx)} unique terms in index.")