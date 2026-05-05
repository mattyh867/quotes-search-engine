
def print_word(index, word):
    """Print the inverted index entry for a single word."""
    word = word.lower()
    postings = index.get(word)

    if not postings:
        print(f"'{word}' not found in the index.")
        return

    total_freq = sum(p["freq"] for p in postings.values())
    print(f"'{word}': {total_freq} occurrence(s) across {len(postings)} page(s)")
    for url, info in sorted(postings.items()):
        print(f"{url}")
        print(f"freq={info['freq']}, positions={info.get('positions', [])}")


def find(index, query):
    """Return URLs of pages containing all words in the query.

    Results are ranked by total frequency of the query terms across the page,
    most-frequent first. Ties broken alphabetically by URL.
    """
    if not query:
        return []

    query = [w.lower() for w in query]
    postings_per_word = []

    for word in query:
        postings = index.get(word)
        if not postings:
            return []
        postings_per_word.append(postings)

    common_urls = set.intersection(*(set(p.keys()) for p in postings_per_word))

    def total_freq(url):
        return sum(p[url]["freq"] for p in postings_per_word)

    return sorted(common_urls, key=lambda u: (-total_freq(u), u))