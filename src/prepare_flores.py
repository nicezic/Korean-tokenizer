import argparse
import hashlib
import json
from pathlib import Path

DATASET_REPO = "openlanguagedata/flores_plus"
DATASET_VERSION = "4.6"
CONFIG = "kor_Hang"
SPLIT = "devtest"
EXPECTED_ROWS = 1012


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_devtest(path, expected_rows=EXPECTED_ROWS):
    rows = []
    seen_ids = set()
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}") from exc

            if not isinstance(row, dict):
                raise ValueError(f"FLORES+ line {line_number} must be a JSON object")
            if row.get("iso_639_3") != "kor" or row.get("iso_15924") != "Hang":
                raise ValueError(f"FLORES+ line {line_number} is not Korean Hangul")
            if row.get("split") != SPLIT:
                raise ValueError(f"FLORES+ line {line_number} is not split={SPLIT}")

            row_id = row.get("id")
            if not isinstance(row_id, str) or not row_id:
                raise ValueError(f"FLORES+ line {line_number} has no string id")
            if row_id in seen_ids:
                raise ValueError(f"Duplicate FLORES+ id: {row_id}")
            seen_ids.add(row_id)

            text = row.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError(f"FLORES+ line {line_number} has no text")
            if "\n" in text or "\r" in text:
                raise ValueError(f"FLORES+ line {line_number} contains an embedded newline")

            rows.append((row_id, text))

    if len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} FLORES+ {CONFIG}/{SPLIT} rows, found {len(rows)}")
    return rows


def prepare_flores(input_path, output_dir, revision, dataset_version=DATASET_VERSION, expected_rows=EXPECTED_ROWS):
    if not revision or revision == "main":
        raise ValueError("Pin FLORES+ with an immutable revision instead of 'main'")

    rows = load_devtest(input_path, expected_rows=expected_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / "kor_Hang_devtest.txt"
    metadata_path = output_dir / "metadata.json"

    prepared_text = "".join(f"{text}\n" for _, text in rows)
    text_path.write_text(prepared_text, encoding="utf-8", newline="")
    prepared_bytes = prepared_text.encode("utf-8")

    metadata = {
        "dataset": DATASET_REPO,
        "dataset_version": dataset_version,
        "revision": revision,
        "config": CONFIG,
        "split": SPLIT,
        "rows": len(rows),
        "first_id": rows[0][0],
        "last_id": rows[-1][0],
        "source": {
            "path": str(input_path),
            "bytes": input_path.stat().st_size,
            "sha256": file_sha256(input_path),
        },
        "prepared": {
            "path": str(text_path),
            "bytes": len(prepared_bytes),
            "characters": len(prepared_text),
            "sha256": hashlib.sha256(prepared_bytes).hexdigest(),
        },
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Prepare pinned FLORES+ Korean devtest text for tokenizer evaluation.")
    parser.add_argument("--input", type=Path, default=Path("data/flores_plus/devtest/kor_Hang.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/flores_plus/prepared"))
    parser.add_argument(
        "--revision", required=True, help="Immutable Hugging Face dataset commit used for the input file."
    )
    parser.add_argument("--dataset-version", default=DATASET_VERSION)
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(
            f"FLORES+ input not found: {args.input}. Accept the dataset terms and obtain {CONFIG}/{SPLIT} first."
        )

    metadata = prepare_flores(args.input, args.output_dir, args.revision, args.dataset_version)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
