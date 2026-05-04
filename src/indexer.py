import re


def tokenise(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.split()


if __name__ == "__main__":
    sample = "Hello, world! TEST -- with punctuation... and numbers 123."
    print(tokenise(sample))