import re
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


if __name__ == "__main__":
    idx = make_index()
    add_page(idx, "http://example.com/a", "The quick brown fox jumps over the lazy dog")
    add_page(idx, "http://example.com/b", "The dog barked at the fox")

    print("the:", dict(idx["the"]))
    print("fox:", dict(idx["fox"]))
    print("dog:", dict(idx["dog"]))