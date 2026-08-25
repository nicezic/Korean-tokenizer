import sys

import tiktoken

from hangul_metrics import print_report, summarize_vocab


def safe_decode(enc, token_id):
    try:
        return enc.decode_bytes([token_id])
    except Exception:
        return None


def main(encoding_names):
    for name in encoding_names:
        enc = tiktoken.get_encoding(name)
        stats = summarize_vocab(safe_decode(enc, i) for i in range(enc.n_vocab))
        print_report(name, stats, "none (byte-level BPE)", lambda t, enc=enc: len(enc.encode(t)))


if __name__ == "__main__":
    main(sys.argv[1:] or ["cl100k_base", "o200k_base"])
