import argparse
import sys

from crawler import crawl
from indexer import load_index, save_index
from search import print_word


DEFAULT_INDEX_PATH = "data/index.json"
DEFAULT_SEED = "https://quotes.toscrape.com/"


def cmd_build(args):
    print(f"Crawling {args.seed} ...")
    index = crawl(seed=args.seed, max_pages=args.max_pages)
    save_index(index, args.output)
    print(f"Done. {len(index)} unique terms written to {args.output}")


def _load_or_exit(path):
    try:
        return load_index(path)
    except FileNotFoundError:
        print(f"No index found at {path}. Run 'build' first.")
        sys.exit(1)


def cmd_load(args):
    index = _load_or_exit(args.input)
    total_postings = sum(len(postings) for postings in index.values())
    print(f"Loaded index from {args.input}")
    print(f"  {len(index)} unique terms")
    print(f"  {total_postings} term-document postings")
    return index


def cmd_print(args):
    index = _load_or_exit(args.input)
    print_word(index, args.word)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="search-tool",
        description="A small web crawler and search tool.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Crawl and build the index.")
    p_build.add_argument("--seed", default=DEFAULT_SEED, help="Seed URL to start crawling from.")
    p_build.add_argument("--output", default=DEFAULT_INDEX_PATH, help="Where to write the index JSON.")
    p_build.add_argument("--max-pages", type=int, default=None, help="Optional cap on pages crawled.")
    p_build.set_defaults(func=cmd_build)

    # load
    p_load = sub.add_parser("load", help="Load a saved index and show stats.")
    p_load.add_argument("--input", default=DEFAULT_INDEX_PATH, help="Path to index JSON.")
    p_load.set_defaults(func=cmd_load)

    # print
    p_print = sub.add_parser("print", help="Print the inverted index entry for a word.")
    p_print.add_argument("word", help="The word to look up.")
    p_print.add_argument("--input", default=DEFAULT_INDEX_PATH, help="Path to index JSON.")
    p_print.set_defaults(func=cmd_print)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()