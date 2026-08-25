import argparse
import hashlib
import json
from pathlib import Path


def iter_documents(path):
    document = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            line = line.rstrip("\n")
            if line:
                document.append(line)
            elif document:
                yield document
                document = []
    if document:
        yield document


def is_test_document(document, test_basis_points):
    digest = hashlib.sha256("\n".join(document).encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    return bucket < test_basis_points


def empty_stats():
    return {"documents": 0, "lines": 0, "characters": 0}


def add_document(stats, document):
    stats["documents"] += 1
    stats["lines"] += len(document)
    stats["characters"] += sum(map(len, document))


def write_document(handle, document):
    handle.write("\n".join(document))
    handle.write("\n\n")


def main():
    parser = argparse.ArgumentParser(description="Deterministically split an article-delimited text corpus.")
    parser.add_argument("--input", type=Path, default=Path("data/kowiki.txt"))
    parser.add_argument("--train", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--test", type=Path, default=Path("data/test.txt"))
    parser.add_argument("--stats", type=Path, default=Path("data/split_stats.json"))
    parser.add_argument("--test-percent", type=float, default=5.0)
    args = parser.parse_args()

    test_basis_points = round(args.test_percent * 100)
    if not 1 <= test_basis_points <= 9999:
        raise SystemExit("--test-percent must be between 0.01 and 99.99")

    args.train.parent.mkdir(parents=True, exist_ok=True)
    args.test.parent.mkdir(parents=True, exist_ok=True)
    stats = {
        "method": "sha256-content-hash",
        "test_basis_points": test_basis_points,
        "train": empty_stats(),
        "test": empty_stats(),
    }

    with (
        args.train.open("w", encoding="utf-8", newline="\n") as train,
        args.test.open("w", encoding="utf-8", newline="\n") as test,
    ):
        for document in iter_documents(args.input):
            target_name = "test" if is_test_document(document, test_basis_points) else "train"
            target = test if target_name == "test" else train
            write_document(target, document)
            add_document(stats[target_name], document)

    stats["train"]["bytes"] = args.train.stat().st_size
    stats["test"]["bytes"] = args.test.stat().st_size
    args.stats.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
