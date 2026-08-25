import json
import sys

from tokenizers import Tokenizer

from hangul_metrics import byte_to_unicode_table, print_report, summarize_vocab


def main(tokenizer_json_path):
    with open(tokenizer_json_path, encoding="utf-8") as f:
        raw = json.load(f)

    u2b = byte_to_unicode_table()

    def vocab_bytes():
        for token in raw["model"]["vocab"]:
            try:
                yield bytes(u2b[ch] for ch in token)
            except KeyError:
                yield None

    tok = Tokenizer.from_file(tokenizer_json_path)
    normalizer = raw.get("normalizer")
    label = "none" if normalizer is None else normalizer.get("type", str(normalizer))
    print_report(f"{raw['model']['type']} ({tokenizer_json_path})", summarize_vocab(vocab_bytes()), label, lambda t: len(tok.encode(t).ids))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: analyze_tokenizer_json.py <path/to/tokenizer.json>")
    main(sys.argv[1])
