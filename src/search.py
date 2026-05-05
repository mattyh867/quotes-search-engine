
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
    """Return URLs of pages containing all words in the query."""
    if not query:
        return []

    matching_sets = []
    for word in query:
        postings = index.get(word.lower())
        if not postings:
            return []
        matching_sets.append(set(postings.keys()))

    return sorted(set.intersection(*matching_sets))
