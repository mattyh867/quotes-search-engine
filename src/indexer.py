"""
Inverted index for the search tool.
 
The index is a three-level dict::
 
    {term: {url: {"freq": int, "positions": list[int]}}}
 
For each lowercased token we store which URLs contain it, and inside
each URL the total frequency on that page plus the 0-indexed positions
of every occurrence in that page's token stream. The whole thing
serialises to JSON so it can be saved between runs.
"""

import json
import os
import re
import math
from collections import defaultdict


def tokenise(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.split()


def make_index():
    return defaultdict(lambda: defaultdict(lambda: {"freq": 0, "positions": []}))


def add_page(index, url, text):
    tokens = tokenise(text)
    for position, token in enumerate(tokens):
        entry = index[token][url]
        entry["freq"] += 1
        entry["positions"].append(position)
    return index


def save_index(index, path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    plain = {term: dict(postings) for term, postings in index.items()}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(plain, f, ensure_ascii=False, indent=2)


def load_index(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    

def compute_idf(index: Index) -> dict[str, float]:
    """Return {term: idf} for every term in the index using log(N / df)."""
    # N = total number of unique documents across the whole index
    all_urls = set()
    for postings in index.values():
        all_urls.update(postings.keys())
    n_docs = len(all_urls)

    if n_docs == 0:
        return {}

    return {
        term: math.log(n_docs / len(postings))
        for term, postings in index.items()
    }


if __name__ == "__main__":
    idx = make_index()
    add_page(idx, "http://example.com/a", "The quick brown fox jumps over the lazy dog")
    add_page(idx, "http://example.com/b", "The dog barked at the fox")

    save_index(idx, "data/index.json")
    print("Saved.")

    loaded = load_index("data/index.json")
    print(f"Loaded {len(loaded)} terms")
    print("the:", loaded["the"])