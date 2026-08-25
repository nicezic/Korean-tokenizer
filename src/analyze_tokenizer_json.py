import json
import sys

from tokenizers import Tokenizer

from hangul_metrics import byte_to_unicode_table, print_report, summarize_vocab


def vocab_pieces(raw):
    vocab = raw["model"]["vocab"]
    items = vocab.keys() if isinstance(vocab, dict) else (entry[0] for entry in vocab)
    u2b = byte_to_unicode_table()

    def to_bytes(token):
        text = str(token).replace("\u2581", " ")
        try:
            return bytes(u2b[ch] for ch in text)
        except KeyError:
            return text.encode("utf-8")

    yield from map(to_bytes, items)


def main(tokenizer_json_path):
    with open(tokenizer_json_path, encoding="utf-8") as f:
        raw = json.load(f)

    tok = Tokenizer.from_file(tokenizer_json_path)
    normalizer = raw.get("normalizer")
    label = "none" if normalizer is None else normalizer.get("type", str(normalizer))
    print_report(
        f"{raw['model']['type']} ({tokenizer_json_path})",
        summarize_vocab(vocab_pieces(raw)),
        label,
        lambda t: len(tok.encode(t).ids),
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: analyze_tokenizer_json.py <path/to/tokenizer.json>")
    main(sys.argv[1])
