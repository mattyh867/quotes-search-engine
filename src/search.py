from indexer import tokenise


def _normalise_query(words):
    """Apply the indexer's tokenisation to each query word."""
    tokens = []
    for word in words:
        tokens.extend(tokenise(word))
    return tokens


def print_word(index, word):
    """Print the inverted index entry for a single word."""
    tokens = tokenise(word)
    if not tokens:
        print(f"'{word}' contains no searchable characters.")
        return

    # if the user typed something like "don't", just look up the first piece
    # and let them know we split it
    lookup = tokens[0]
    if len(tokens) > 1:
        print(f"(treating '{word}' as {tokens} — showing '{lookup}')")

    postings = index.get(lookup)
    if not postings:
        print(f"'{lookup}' not found in the index.")
        return

    total_freq = sum(p["freq"] for p in postings.values())
    print(f"'{lookup}': {total_freq} occurrence(s) across {len(postings)} page(s)")
    for url, info in sorted(postings.items()):
        print(f"  {url}")
        print(f"    freq={info['freq']}, positions={info.get('positions', [])}")


def find(index, query):
    """Return (urls, normalised_query) for pages containing all query words."""
    query = _normalise_query(query)
    if not query:
        return [], []

    postings_per_word = []
    for word in query:
        postings = index.get(word)
        if not postings:
            return [], query
        postings_per_word.append(postings)

    common_urls = set.intersection(*(set(p.keys()) for p in postings_per_word))

    def total_freq(url):
        return sum(p[url]["freq"] for p in postings_per_word)

    ranked = sorted(common_urls, key=lambda u: (-total_freq(u), u))
    return ranked, query