import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

import sentencepiece as spm

PROBE_NFC = "한"
PROBE_NFD = unicodedata.normalize("NFD", PROBE_NFC)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def common_config(input_path, vocab_size):
    return {
        "input": str(input_path),
        "model_type": "bpe",
        "vocab_size": vocab_size,
        "character_coverage": 0.9995,
        "input_sentence_size": 0,
        "shuffle_input_sentence": False,
        "max_sentence_length": 8192,
        "max_sentencepiece_length": 64,
        "num_threads": 10,
        "unk_id": 0,
        "bos_id": 1,
        "eos_id": 2,
        "pad_id": -1,
        "hard_vocab_limit": True,
        "byte_fallback": True,
    }


def train_variant(name, output_dir, common, *, normalization_rule_name=None, normalization_tsv=None):
    if (normalization_rule_name is None) == (normalization_tsv is None):
        raise ValueError("Specify exactly one normalization mode.")

    config = dict(common)
    config["model_prefix"] = str(output_dir / name)
    if normalization_rule_name is not None:
        config["normalization_rule_name"] = normalization_rule_name
    else:
        config["normalization_rule_tsv"] = str(normalization_tsv)
    spm.SentencePieceTrainer.train(**config)
    return config


def assert_fair_configs(baseline, jamo):
    ignored = {"model_prefix", "normalization_rule_name", "normalization_rule_tsv"}
    baseline_common = {key: value for key, value in baseline.items() if key not in ignored}
    jamo_common = {key: value for key, value in jamo.items() if key not in ignored}
    if baseline_common != jamo_common:
        raise RuntimeError("Effective configs differ outside normalization.")


def normalization_probe(model_path):
    processor = spm.SentencePieceProcessor(model_file=str(model_path))
    return {
        "nfc_input": PROBE_NFC,
        "nfd_input": PROBE_NFD,
        "nfc_normalized": processor.normalize(PROBE_NFC),
        "nfd_normalized": processor.normalize(PROBE_NFD),
        "nfc_pieces": processor.encode(PROBE_NFC, out_type=str),
        "nfd_pieces": processor.encode(PROBE_NFD, out_type=str),
    }


def assert_normalization_contract(baseline_probe, jamo_probe):
    if baseline_probe["nfc_normalized"] == baseline_probe["nfd_normalized"]:
        raise RuntimeError("Identity baseline unexpectedly collapses NFC and NFD probe forms.")
    if jamo_probe["nfc_normalized"] != jamo_probe["nfd_normalized"]:
        raise RuntimeError("Jamo normalizer does not converge NFC and NFD probe forms.")
    if PROBE_NFD not in jamo_probe["nfc_normalized"]:
        raise RuntimeError("Jamo normalizer did not decompose the NFC probe into conjoining Jamo.")


def assert_nfkc_control_contract(control_probe):
    if control_probe["nfc_normalized"] != control_probe["nfd_normalized"]:
        raise RuntimeError("NFKC control does not converge NFC and NFD probe forms.")
    if PROBE_NFC not in control_probe["nfc_normalized"]:
        raise RuntimeError("NFKC control did not compose the NFD probe into the precomposed syllable.")


def auxiliary_name(vocab_size):
    return f"jamo-{vocab_size // 1000}k" if vocab_size % 1000 == 0 else f"jamo-{vocab_size}"


def main():
    parser = argparse.ArgumentParser(description="Train controlled baseline and Jamo-aware SentencePiece BPE models.")
    parser.add_argument("--input", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    parser.add_argument("--jamo-tsv", type=Path, default=Path("data/korean_hangul_jamo.tsv"))
    parser.add_argument("--vocab-size", type=int, default=32_000)
    parser.add_argument("--aux-jamo-vocab-size", type=int)
    parser.add_argument("--with-nfkc-control", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    common = common_config(args.input, args.vocab_size)
    baseline = train_variant(
        "baseline",
        args.output_dir,
        common,
        normalization_rule_name="identity",
    )
    jamo = train_variant(
        "jamo",
        args.output_dir,
        common,
        normalization_tsv=args.jamo_tsv,
    )
    assert_fair_configs(baseline, jamo)

    baseline_probe = normalization_probe(args.output_dir / "baseline.model")
    jamo_probe = normalization_probe(args.output_dir / "jamo.model")
    assert_normalization_contract(baseline_probe, jamo_probe)

    canonical_control = None
    if args.with_nfkc_control:
        control_config = train_variant(
            "nfkc",
            args.output_dir,
            common,
            normalization_rule_name="nmt_nfkc",
        )
        assert_fair_configs(baseline, control_config)
        control_probe = normalization_probe(args.output_dir / "nfkc.model")
        assert_nfkc_control_contract(control_probe)
        canonical_control = {"config": control_config, "normalization_probe": control_probe}

    auxiliary = None
    if args.aux_jamo_vocab_size is not None:
        if args.aux_jamo_vocab_size >= args.vocab_size:
            raise SystemExit("--aux-jamo-vocab-size must be smaller than --vocab-size")
        aux_name = auxiliary_name(args.aux_jamo_vocab_size)
        aux_common = common_config(args.input, args.aux_jamo_vocab_size)
        aux_config = train_variant(
            aux_name,
            args.output_dir,
            aux_common,
            normalization_tsv=args.jamo_tsv,
        )
        aux_probe = normalization_probe(args.output_dir / f"{aux_name}.model")
        if aux_probe["nfc_normalized"] != aux_probe["nfd_normalized"]:
            raise RuntimeError("Auxiliary Jamo model does not converge NFC and NFD probe forms.")
        auxiliary = {"name": aux_name, "config": aux_config, "normalization_probe": aux_probe}

    audit = {
        "sentencepiece_version": spm.__version__,
        "input": {
            "path": str(args.input),
            "bytes": args.input.stat().st_size,
            "sha256": file_sha256(args.input),
        },
        "jamo_tsv": {
            "path": str(args.jamo_tsv),
            "bytes": args.jamo_tsv.stat().st_size,
            "sha256": file_sha256(args.jamo_tsv),
        },
        "primary": {
            "common": common,
            "experimental_difference": {
                "baseline": {"normalization_rule_name": "identity"},
                "jamo": {"normalization_rule_tsv": str(args.jamo_tsv)},
            },
            "normalization_probe": {
                "baseline": baseline_probe,
                "jamo": jamo_probe,
            },
        },
        "canonical_control": canonical_control,
        "auxiliary": auxiliary,
    }
    config_path = args.output_dir / "training_config.json"
    config_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
