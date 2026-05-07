"""
Query handling for the search tool.
 
'print_word' shows the inverted-index entry for a single term, and
'find' runs an AND-style multi-word query and ranks the matching pages
by total frequency across the query terms. Both apply the indexer's
tokeniser to incoming queries so the search side and the indexing side
agree on what counts as a token.
"""

from indexer import tokenise, Index, compute_idf


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


def find(index: Index, query: list[str]) -> tuple[list[str], list[str]]:
    """
    Find pages containing every word in 'query', ranked by TF-IDF.

    Returns (ranked_urls, normalised_query). The normalised query is
    handed back so the caller can show it to the user when it differs
    from what they typed (e.g. "Good!" → "good").
    """
    query = _normalise_query(query)
    if not query:
        return [], []

    postings_per_word = []
    for word in query:
        postings = index.get(word)
        if not postings:
            return [], query
        postings_per_word.append((word, postings))

    common_urls = set.intersection(*(set(p.keys()) for _, p in postings_per_word))

    # Compute IDF once for this query rather than per-page.
    idf = compute_idf(index)

    def tf_idf_score(url: str) -> float:
        return sum(
            postings[url]["freq"] * idf.get(word, 0.0)
            for word, postings in postings_per_word
        )

    # Highest TF-IDF first, then alphabeticalally by URL as a tiebreaker
    ranked = sorted(common_urls, key=lambda u: (-tf_idf_score(u), u))
    return ranked, query