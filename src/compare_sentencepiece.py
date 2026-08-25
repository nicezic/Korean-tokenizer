import argparse
import json
import statistics
import unicodedata
from collections import Counter
from pathlib import Path

import sentencepiece as spm

from hangul_metrics import JAMO_RANGES, SAMPLE, SYLLABLE_MAX, SYLLABLE_MIN
from split_corpus import iter_documents
from train_sentencepiece import file_sha256, normalization_probe


def dataset_metadata(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": file_sha256(path)}


def is_syllable(char):
    return SYLLABLE_MIN <= ord(char) <= SYLLABLE_MAX


def is_jamo(char):
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in JAMO_RANGES)


def vocab_anatomy(processor):
    atomic = set()
    recomposed_atomic = set()
    multi = recomposed_multi = jamo = max_recomposed_syllables = 0
    for piece_id in range(processor.vocab_size()):
        piece = processor.id_to_piece(piece_id).replace("▁", "")
        syllables = sum(map(is_syllable, piece))
        if syllables == 1 and len(piece) == 1:
            atomic.add(piece)
        elif syllables >= 2:
            multi += 1
        if any(map(is_jamo, piece)):
            jamo += 1

        recomposed = unicodedata.normalize("NFC", piece)
        recomposed_syllables = sum(map(is_syllable, recomposed))
        max_recomposed_syllables = max(max_recomposed_syllables, recomposed_syllables)
        if recomposed_syllables == 1 and len(recomposed) == 1:
            recomposed_atomic.add(recomposed)
        elif recomposed_syllables >= 2:
            recomposed_multi += 1

    return {
        "vocab_size": processor.vocab_size(),
        "atomic_syllables": len(atomic),
        "multi_syllable_merges": multi,
        "jamo_pieces": jamo,
        "recomposed_atomic_syllables": len(recomposed_atomic),
        "recomposed_multi_syllable_merges": recomposed_multi,
        "max_recomposed_syllables_per_piece": max_recomposed_syllables,
    }


def token_stats(processor, text):
    ids = processor.encode(text, out_type=int)
    return len(ids), ids.count(processor.unk_id())


def corpus_metrics(processor, path):
    doc_tokens = []
    doc_hangul = []
    nfc_total = nfd_total = nfc_unk_total = nfd_unk_total = total_chars = total_bytes = 0
    for document in iter_documents(path):
        text = "\n".join(document)
        nfc = unicodedata.normalize("NFC", text)
        nfd = unicodedata.normalize("NFD", text)
        nfc_tokens, nfc_unk = token_stats(processor, nfc)
        nfd_tokens, nfd_unk = token_stats(processor, nfd)
        hangul = sum(map(is_syllable, nfc))
        doc_tokens.append(nfc_tokens)
        doc_hangul.append(hangul)
        nfc_total += nfc_tokens
        nfd_total += nfd_tokens
        nfc_unk_total += nfc_unk
        nfd_unk_total += nfd_unk
        total_chars += len(nfc)
        total_bytes += len(nfc.encode("utf-8"))
    total_hangul = sum(doc_hangul)
    return {
        "documents": len(doc_tokens),
        "characters": total_chars,
        "utf8_bytes": total_bytes,
        "hangul_syllables": total_hangul,
        "nfc_tokens": nfc_total,
        "nfd_tokens": nfd_total,
        "nfc_unk_tokens": nfc_unk_total,
        "nfd_unk_tokens": nfd_unk_total,
        "nfd_blowup": round(nfd_total / nfc_total, 4),
        "bytes_per_token": round(total_bytes / nfc_total, 4) if nfc_total else None,
        "characters_per_token": round(total_chars / nfc_total, 4) if nfc_total else None,
        "tokens_per_character": round(nfc_total / total_chars, 4) if total_chars else None,
        "tokens_per_hangul_syllable": round(nfc_total / total_hangul, 4) if total_hangul else None,
        "mean_tokens_per_document": round(statistics.fmean(doc_tokens), 2),
        "median_tokens_per_document": statistics.median(doc_tokens),
    }


def syllable_counts(path):
    counts = Counter()
    with path.open(encoding="utf-8") as source:
        for line in source:
            counts.update(char for char in line if is_syllable(char))
    return counts


def rare_tail_metrics(processor, train_counts, test_counts, max_train_occurrences=5):
    rare_train = {char for char, occurrences in train_counts.items() if occurrences <= max_train_occurrences}
    test_rare = Counter({char: test_counts[char] for char in rare_train if test_counts[char]})
    unseen = Counter({char: occurrences for char, occurrences in test_counts.items() if not train_counts[char]})

    weighted_tokens = weighted_byte_tokens = 0
    examples = []
    for char, test_occurrences in test_rare.most_common():
        pieces = processor.encode(char, out_type=str)
        weighted_tokens += len(pieces) * test_occurrences
        weighted_byte_tokens += sum(piece.startswith("<0x") for piece in pieces) * test_occurrences
        if len(examples) < 20:
            examples.append(
                {
                    "syllable": char,
                    "train_occurrences": train_counts[char],
                    "test_occurrences": test_occurrences,
                    "pieces": pieces,
                }
            )

    total_rare_occurrences = sum(test_rare.values())
    return {
        "max_train_occurrences": max_train_occurrences,
        "rare_train_types": len(rare_train),
        "test_rare_types": len(test_rare),
        "test_rare_occurrences": total_rare_occurrences,
        "mean_isolated_tokens_per_rare_occurrence": round(weighted_tokens / total_rare_occurrences, 4)
        if total_rare_occurrences
        else None,
        "mean_byte_tokens_per_rare_occurrence": round(weighted_byte_tokens / total_rare_occurrences, 4)
        if total_rare_occurrences
        else None,
        "unique_unseen_syllables": len(unseen),
        "unseen_occurrences": sum(unseen.values()),
        "examples": examples,
    }


def sample_metrics(processor):
    nfc = unicodedata.normalize("NFC", SAMPLE)
    nfd = unicodedata.normalize("NFD", SAMPLE)
    nfc_tokens, nfc_unk = token_stats(processor, nfc)
    nfd_tokens, nfd_unk = token_stats(processor, nfd)
    return {
        "characters": len(nfc),
        "nfc_tokens": nfc_tokens,
        "nfd_tokens": nfd_tokens,
        "nfc_unk_tokens": nfc_unk,
        "nfd_unk_tokens": nfd_unk,
        "nfd_blowup": round(nfd_tokens / nfc_tokens, 4),
    }


def evaluate(name, model_path, test_path, train_counts, test_counts):
    processor = spm.SentencePieceProcessor(model_file=str(model_path))
    return {
        "name": name,
        "model": str(model_path),
        "normalization_probe": normalization_probe(model_path),
        "vocab": vocab_anatomy(processor),
        "readme_sample": sample_metrics(processor),
        "held_out": corpus_metrics(processor, test_path),
        "rare_tail": rare_tail_metrics(processor, train_counts, test_counts),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare baseline and Jamo-aware SentencePiece models.")
    parser.add_argument("--train", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--test", type=Path, default=Path("data/test.txt"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--output", type=Path, default=Path("data/sentencepiece_results.json"))
    args = parser.parse_args()

    train_counts = syllable_counts(args.train)
    test_counts = syllable_counts(args.test)
    results = {
        "sentencepiece_version": spm.__version__,
        "datasets": {"train": dataset_metadata(args.train), "test": dataset_metadata(args.test)},
        "training_seen_hangul_syllables": len(train_counts),
        "baseline": evaluate("baseline", args.models_dir / "baseline.model", args.test, train_counts, test_counts),
        "jamo": evaluate("jamo", args.models_dir / "jamo.model", args.test, train_counts, test_counts),
        "controls": {},
        "auxiliary": {},
    }
    nfkc_model = args.models_dir / "nfkc.model"
    if nfkc_model.exists():
        results["controls"]["nfkc"] = evaluate("nfkc", nfkc_model, args.test, train_counts, test_counts)
    for model_path in sorted(args.models_dir.glob("jamo-*.model")):
        name = model_path.stem
        results["auxiliary"][name] = evaluate(name, model_path, args.test, train_counts, test_counts)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
