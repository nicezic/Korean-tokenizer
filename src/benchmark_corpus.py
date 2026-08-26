import argparse
import hashlib
import json
import statistics
import unicodedata
from pathlib import Path

import sentencepiece as spm
import tiktoken
from tokenizers import Tokenizer

from analyze_tiktoken_encoding import safe_decode
from analyze_tokenizer_json import vocab_pieces
from hangul_metrics import SYLLABLE_MAX, SYLLABLE_MIN, summarize_vocab
from prepare_cc100 import JAMO_TSV_SHA256, load_jamo_translation

PROJECT_ROOT = Path(__file__).parents[1]


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def is_hangul_syllable(char):
    return SYLLABLE_MIN <= ord(char) <= SYLLABLE_MAX


def percentile(sorted_values, quantile):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def distribution_summary(values):
    ordered = sorted(values)
    if not ordered:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
        }
    return {
        "count": len(ordered),
        "mean": round(statistics.fmean(ordered), 4),
        "min": ordered[0],
        "p25": round(percentile(ordered, 0.25), 4),
        "median": round(percentile(ordered, 0.5), 4),
        "p75": round(percentile(ordered, 0.75), 4),
        "p95": round(percentile(ordered, 0.95), 4),
        "max": ordered[-1],
    }


def resolve_recorded_path(recorded_path):
    path = Path(recorded_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_flores_units(text_path, metadata_path):
    text_path = text_path.resolve()
    metadata_path = metadata_path.resolve()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    prepared = metadata["prepared"]

    if text_path.stat().st_size != prepared["bytes"]:
        raise RuntimeError("FLORES+ prepared text byte count differs from metadata")
    digest = file_sha256(text_path)
    if digest != prepared["sha256"]:
        raise RuntimeError(f"FLORES+ prepared text SHA-256 mismatch: {digest}")

    recorded_path = resolve_recorded_path(prepared["path"]).resolve()
    if recorded_path != text_path:
        raise RuntimeError(f"FLORES+ metadata points to a different prepared file: {recorded_path}")

    units = []
    with text_path.open(encoding="utf-8", newline="") as source:
        for line_number, line in enumerate(source, 1):
            if not line.endswith("\n"):
                raise RuntimeError(f"FLORES+ prepared sentence {line_number} is missing its line terminator")
            text = line[:-1]
            if not text:
                raise RuntimeError(f"FLORES+ prepared sentence {line_number} is empty")
            if "\n" in text or "\r" in text:
                raise RuntimeError(f"FLORES+ prepared sentence {line_number} contains an embedded newline")
            units.append(text)

    if len(units) != metadata["rows"]:
        raise RuntimeError(f"FLORES+ row count mismatch: {len(units)} != {metadata['rows']}")
    return units, {
        "metadata_path": str(metadata_path),
        "metadata_sha256": file_sha256(metadata_path),
        "text_path": str(text_path),
        "text_sha256": digest,
        "rows": len(units),
        "dataset": metadata["dataset"],
        "dataset_version": metadata["dataset_version"],
        "revision": metadata["revision"],
        "config": metadata["config"],
        "split": metadata["split"],
    }


class HFJsonCounter:
    def __init__(self, tokenizer_path, translation=None):
        self.path = tokenizer_path.resolve()
        self.tokenizer = Tokenizer.from_file(str(self.path))
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        unk_token = raw.get("model", {}).get("unk_token")
        self.unk_id = self.tokenizer.token_to_id(unk_token) if unk_token else None
        self.translation = translation
        self.vocab_stats = summarize_vocab(vocab_pieces(raw))

    def count(self, text):
        if self.translation is not None:
            text = text.translate(self.translation)
        ids = self.tokenizer.encode(text, add_special_tokens=False).ids
        unknowns = ids.count(self.unk_id) if self.unk_id is not None else 0
        return len(ids), unknowns

    def identity(self):
        return {
            "kind": "hf-json",
            "path": str(self.path),
            "bytes": self.path.stat().st_size,
            "sha256": file_sha256(self.path),
            "vocab": self.vocab_stats,
        }


class TiktokenCounter:
    def __init__(self, encoding_name):
        self.encoding_name = encoding_name
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.vocab_stats = summarize_vocab(
            safe_decode(self.encoding, token_id) for token_id in range(self.encoding.n_vocab)
        )

    def count(self, text):
        ids = self.encoding.encode(text, allowed_special=set(), disallowed_special=())
        return len(ids), 0

    def identity(self):
        return {
            "kind": "tiktoken",
            "encoding": self.encoding_name,
            "tiktoken_version": tiktoken.__version__,
            "vocab": self.vocab_stats,
        }


def sentencepiece_vocab_bytes(processor):
    for piece_id in range(processor.vocab_size()):
        piece = processor.id_to_piece(piece_id)
        if len(piece) == 6 and piece.startswith("<0x") and piece.endswith(">"):
            try:
                yield bytes([int(piece[3:5], 16)])
                continue
            except ValueError:
                pass
        yield piece.replace("▁", " ").encode("utf-8")


class SentencePieceCounter:
    def __init__(self, model_path):
        self.path = model_path.resolve()
        self.processor = spm.SentencePieceProcessor(model_file=str(self.path))
        self.vocab_stats = summarize_vocab(sentencepiece_vocab_bytes(self.processor))

    def count(self, text):
        ids = self.processor.encode(text, out_type=int)
        unk_id = self.processor.unk_id()
        return len(ids), ids.count(unk_id) if unk_id >= 0 else 0

    def identity(self):
        return {
            "kind": "sentencepiece",
            "path": str(self.path),
            "bytes": self.path.stat().st_size,
            "sha256": file_sha256(self.path),
            "sentencepiece_version": spm.__version__,
            "vocab": self.vocab_stats,
        }


def corpus_metrics(counter, units):
    per_sentence_tokens = []
    per_sentence_nfd_tokens = []
    total_chars = 0
    total_bytes = 0
    total_hangul = 0
    nfc_total = 0
    nfd_total = 0
    nfc_unk_total = 0
    nfd_unk_total = 0

    for text in units:
        nfc = unicodedata.normalize("NFC", text)
        nfd = unicodedata.normalize("NFD", nfc)
        nfc_tokens, nfc_unknowns = counter.count(nfc)
        nfd_tokens, nfd_unknowns = counter.count(nfd)
        hangul = sum(map(is_hangul_syllable, nfc))

        per_sentence_tokens.append(nfc_tokens)
        per_sentence_nfd_tokens.append(nfd_tokens)
        nfc_total += nfc_tokens
        nfd_total += nfd_tokens
        nfc_unk_total += nfc_unknowns
        nfd_unk_total += nfd_unknowns
        total_chars += len(nfc)
        total_bytes += len(nfc.encode("utf-8"))
        total_hangul += hangul

    return {
        "sentences": len(units),
        "characters": total_chars,
        "utf8_bytes": total_bytes,
        "hangul_syllables": total_hangul,
        "nfc_tokens": nfc_total,
        "nfd_tokens": nfd_total,
        "nfc_unk_tokens": nfc_unk_total,
        "nfd_unk_tokens": nfd_unk_total,
        "nfd_nfc_ratio": round(nfd_total / nfc_total, 6) if nfc_total else None,
        "bytes_per_token": round(total_bytes / nfc_total, 6) if nfc_total else None,
        "characters_per_token": round(total_chars / nfc_total, 6) if nfc_total else None,
        "tokens_per_hangul_syllable": round(nfc_total / total_hangul, 6) if total_hangul else None,
        "nfc_tokens_per_sentence": distribution_summary(per_sentence_tokens),
        "nfd_tokens_per_sentence": distribution_summary(per_sentence_nfd_tokens),
    }


def build_counter(kind, tokenizer, representation, jamo_tsv):
    translation = None
    representation_contract = {"mode": representation}
    if representation == "jamo":
        if kind != "hf-json":
            raise ValueError("Explicit Jamo representation is supported only for experimental HF tokenizer.json models")
        jamo_tsv = jamo_tsv.resolve()
        digest = file_sha256(jamo_tsv)
        if digest != JAMO_TSV_SHA256:
            raise RuntimeError(f"Unexpected Jamo TSV SHA-256: {digest}")
        translation = load_jamo_translation(jamo_tsv)
        representation_contract["jamo_tsv"] = {
            "path": str(jamo_tsv),
            "bytes": jamo_tsv.stat().st_size,
            "sha256": digest,
            "entries": len(translation),
        }

    if kind == "hf-json":
        return HFJsonCounter(Path(tokenizer), translation=translation), representation_contract
    if kind == "tiktoken":
        if representation != "native":
            raise ValueError("tiktoken benchmarks must use representation=native")
        return TiktokenCounter(tokenizer), representation_contract
    if kind == "sentencepiece":
        if representation != "native":
            raise ValueError("SentencePiece models own their normalization and must use representation=native")
        return SentencePieceCounter(Path(tokenizer)), representation_contract
    raise ValueError(f"Unsupported tokenizer kind: {kind}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark tokenizers on one pinned Korean reference corpus.")
    parser.add_argument("--kind", choices=("hf-json", "tiktoken", "sentencepiece"), required=True)
    parser.add_argument("--tokenizer", required=True, help="tokenizer.json/model path, or tiktoken encoding name")
    parser.add_argument("--name", required=True)
    parser.add_argument("--representation", choices=("native", "precomposed", "jamo"), default="native")
    parser.add_argument("--input", type=Path, default=Path("data/flores_plus/prepared/kor_Hang_devtest.txt"))
    parser.add_argument("--metadata", type=Path, default=Path("data/flores_plus/prepared/metadata.json"))
    parser.add_argument("--jamo-tsv", type=Path, default=Path("data/korean_hangul_jamo.tsv"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    units, dataset = load_flores_units(args.input, args.metadata)
    counter, representation_contract = build_counter(args.kind, args.tokenizer, args.representation, args.jamo_tsv)
    result = {
        "name": args.name,
        "representation": representation_contract,
        "dataset": dataset,
        "tokenizer": counter.identity(),
        "metrics": corpus_metrics(counter, units),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
