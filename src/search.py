
def print_word(index, word):
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
