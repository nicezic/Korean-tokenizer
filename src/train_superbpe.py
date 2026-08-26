import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

SUPERBPE_COMMIT = "bbd09768fc28a875cef48e6bdd66e3a17454628e"
TOKENIZERS_SUPERBPE_COMMIT = "757f2a55c0820ed47064e1fe473deea39b7b611b"
VOCAB_SIZE = 32_000
RETAINED_MERGE_LINES = 25_000
STAGE1_REGEX = r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+|[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n/]*|\s*[\r\n]+|\s+(?!\S)|\s+"
STAGE2_REGEX = r"\p{N}{1,3}| ?[^\s\p{L}\p{N}]{2,}[\r\n/]*| +(?!\S)"
PROJECT_ROOT = Path(__file__).parents[1]


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_upstream(upstream_dir):
    upstream_dir = upstream_dir.resolve()
    submodule_dir = upstream_dir / "tokenizers_superbpe"
    if not (upstream_dir / "train_tokenizer.py").is_file():
        raise RuntimeError(f"SuperBPE checkout is incomplete: {upstream_dir}")
    if not submodule_dir.is_dir():
        raise RuntimeError("tokenizers_superbpe submodule is not initialized")

    superbpe_commit = git_output(upstream_dir, "rev-parse", "HEAD")
    tokenizers_commit = git_output(submodule_dir, "rev-parse", "HEAD")
    if superbpe_commit != SUPERBPE_COMMIT:
        raise RuntimeError(f"Unexpected SuperBPE revision: {superbpe_commit}")
    if tokenizers_commit != TOKENIZERS_SUPERBPE_COMMIT:
        raise RuntimeError(f"Unexpected tokenizers_superbpe revision: {tokenizers_commit}")

    tree_entry = git_output(upstream_dir, "ls-tree", "HEAD", "tokenizers_superbpe").split()
    if len(tree_entry) < 3 or tree_entry[2] != TOKENIZERS_SUPERBPE_COMMIT:
        raise RuntimeError("SuperBPE checkout does not pin the expected tokenizers_superbpe submodule")

    return {
        "superbpe_commit": superbpe_commit,
        "tokenizers_superbpe_commit": tokenizers_commit,
    }


def find_rust_tool(name):
    executable = shutil.which(name)
    if executable is not None:
        return executable
    rustup_executable = Path.home() / ".cargo/bin" / name
    return str(rustup_executable) if rustup_executable.is_file() else None


def validate_runtime(python_executable, upstream_dir):
    python_executable = python_executable.resolve()
    if not python_executable.is_file():
        raise RuntimeError(f"Isolated Python executable not found: {python_executable}")

    probe_code = r"""
import importlib.metadata
import json
import sys

for name in ("click", "filelock", "simdjson", "tokenizers"):
    __import__(name)

dist = importlib.metadata.distribution("tokenizers")
print(json.dumps({
    "python": list(sys.version_info[:3]),
    "tokenizers_version": dist.version,
    "tokenizers_direct_url": dist.read_text("direct_url.json"),
}))
"""
    probe = subprocess.run(
        [str(python_executable), "-c", probe_code],
        check=True,
        capture_output=True,
        text=True,
    )
    runtime = json.loads(probe.stdout)
    if runtime["python"][:2] != [3, 12]:
        raise RuntimeError(f"SuperBPE isolated runtime must be Python 3.12, got {runtime['python']}")

    direct_url_text = runtime["tokenizers_direct_url"]
    if not direct_url_text:
        raise RuntimeError("tokenizers installation has no direct_url.json; custom fork identity cannot be audited")
    direct_url = json.loads(direct_url_text)
    expected_source = (upstream_dir / "tokenizers_superbpe" / "bindings" / "python").resolve().as_uri()
    if direct_url.get("url") != expected_source or not direct_url.get("dir_info", {}).get("editable"):
        raise RuntimeError("tokenizers is not the editable custom SuperBPE fork from the pinned checkout")

    rustc = find_rust_tool("rustc")
    cargo = find_rust_tool("cargo")
    if rustc is None or cargo is None:
        raise RuntimeError("Rust toolchain is required: rustc and cargo must both be available")
    rust_version = subprocess.run([rustc, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    cargo_version = subprocess.run([cargo, "--version"], check=True, capture_output=True, text=True).stdout.strip()

    return {
        "python_executable": str(python_executable),
        "python_version": ".".join(map(str, runtime["python"])),
        "tokenizers_version": runtime["tokenizers_version"],
        "tokenizers_source": direct_url["url"],
        "rustc": rust_version,
        "cargo": cargo_version,
    }


def resolve_recorded_path(recorded_path):
    path = Path(recorded_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def validate_corpus_file(path, expected_bytes, expected_sha256):
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"Prepared corpus file not found: {path}")
    if path.name != "train.txt":
        raise RuntimeError(f"Prepared corpus must use a dedicated train.txt: {path}")

    eligible = sorted(
        candidate.resolve()
        for candidate in path.parent.iterdir()
        if candidate.is_file()
        and candidate.suffix == ".txt"
        and "truncated" not in candidate.name
        and "split" not in candidate.name
    )
    if eligible != [path]:
        raise RuntimeError(f"Corpus directory must expose exactly one upstream-eligible .txt file: {path.parent}")

    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise RuntimeError(f"Prepared corpus byte mismatch for {path}: {actual_bytes} != {expected_bytes}")
    actual_sha256 = file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"Prepared corpus SHA-256 mismatch for {path}: {actual_sha256}")
    return {"path": str(path), "bytes": actual_bytes, "sha256": actual_sha256}


def load_scale_inputs(metadata_path, scale):
    metadata_path = metadata_path.resolve()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    try:
        scale_record = metadata["slices"][scale]
    except KeyError as exc:
        raise RuntimeError(f"Scale {scale!r} not found in prepared CC-100 metadata") from exc

    inputs = {}
    for representation, record_key in (("precomposed", "source"), ("jamo", "jamo")):
        record = scale_record[record_key]
        path = resolve_recorded_path(record["path"])
        inputs[representation] = validate_corpus_file(path, record["bytes"], record["sha256"])

    source_documents = scale_record["documents"]
    if source_documents <= 0:
        raise RuntimeError(f"Prepared scale {scale} contains no documents")
    return {
        "metadata_path": str(metadata_path),
        "metadata_sha256": file_sha256(metadata_path),
        "scale": scale,
        "source_budget_bytes": scale_record["budget_bytes"],
        "source_documents": source_documents,
        "first_document_sha256": scale_record["first_document_sha256"],
        "last_document_sha256": scale_record["last_document_sha256"],
        "inputs": inputs,
    }


def output_dirs(output_root, scale):
    scale_root = output_root / scale
    return {
        "precomposed-bpe": scale_root / "precomposed-bpe-32k",
        "jamo-bpe": scale_root / "jamo-bpe-32k",
        "precomposed-superbpe": scale_root / "precomposed-superbpe-32k",
        "jamo-superbpe": scale_root / "jamo-superbpe-32k",
    }


def ensure_new_output_dir(path):
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"Refusing to reuse non-empty tokenizer output directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def run_upstream_training(python_executable, upstream_dir, output_dir, corpus_dir, regex_string):
    command = [
        str(python_executable),
        "-m",
        "train_tokenizer",
        "--output_dir",
        str(output_dir.resolve()),
        "--corpus_dir",
        str(corpus_dir.resolve()),
        "--vocab_size",
        str(VOCAB_SIZE),
        "--regex_string",
        regex_string,
    ]
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    subprocess.run(command, cwd=upstream_dir, env=env, check=True)
    return command


def validate_stage1_output(output_dir, corpus_record):
    required = ["merges.txt", "vocab.json", "tokenizer.json", "meta.json"]
    for name in required:
        if not (output_dir / name).is_file():
            raise RuntimeError(f"Stage-1 output missing {name}: {output_dir}")

    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    expected_path = str(Path(corpus_record["path"]).resolve())
    if meta.get("train_files") != [expected_path]:
        raise RuntimeError(f"Stage-1 meta.json does not contain exactly the prepared corpus: {output_dir}")
    if meta.get("total_bytes") != corpus_record["bytes"]:
        raise RuntimeError(f"Stage-1 meta.json byte count differs from prepared corpus: {output_dir}")


def copy_inherited_merges(stage1_merges, stage2_dir, retained_lines=RETAINED_MERGE_LINES):
    stage2_dir.mkdir(parents=True, exist_ok=True)
    inherited_path = stage2_dir / "inherited_merges.txt"
    seed_path = stage2_dir / "merges.txt"
    lines = []
    with stage1_merges.open(encoding="utf-8") as source:
        for _ in range(retained_lines):
            line = source.readline()
            if not line:
                break
            lines.append(line)

    if len(lines) != retained_lines:
        raise RuntimeError(f"Stage-1 merges.txt has only {len(lines)} lines; need {retained_lines}")
    if not lines[0].startswith("#version:"):
        raise RuntimeError("Stage-1 merges.txt does not begin with a Hugging Face version header")

    content = "".join(lines)
    inherited_path.write_text(content, encoding="utf-8", newline="\n")
    seed_path.write_text(content, encoding="utf-8", newline="\n")
    return {
        "retained_lines": len(lines),
        "inherited_merge_rules": len(lines) - 1,
        "sha256": file_sha256(inherited_path),
        "path": str(inherited_path.resolve()),
    }


def tokenizer_split_regex(tokenizer_json):
    pre_tokenizer = tokenizer_json.get("pre_tokenizer")
    if not isinstance(pre_tokenizer, dict):
        return None
    candidates = pre_tokenizer.get("pretokenizers", []) if pre_tokenizer.get("type") == "Sequence" else [pre_tokenizer]
    for candidate in candidates:
        if candidate.get("type") != "Split":
            continue
        pattern = candidate.get("pattern")
        if isinstance(pattern, dict):
            return pattern.get("Regex")
    return None


def artifact_audit(output_dir, expected_regex):
    audit = {}
    for name in ("meta.json", "vocab.json", "merges.txt", "tokenizer.json"):
        path = output_dir / name
        if not path.is_file():
            raise RuntimeError(f"Tokenizer output missing {name}: {output_dir}")
        audit[name] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}

    vocab = json.loads((output_dir / "vocab.json").read_text(encoding="utf-8"))
    if not isinstance(vocab, dict) or len(vocab) != VOCAB_SIZE:
        size = len(vocab) if isinstance(vocab, dict) else None
        raise RuntimeError(f"Tokenizer vocab size mismatch in {output_dir}: {size} != {VOCAB_SIZE}")

    tokenizer_json = json.loads((output_dir / "tokenizer.json").read_text(encoding="utf-8"))
    actual_regex = tokenizer_split_regex(tokenizer_json)
    if actual_regex != expected_regex:
        raise RuntimeError(f"Tokenizer Split regex mismatch in {output_dir}")

    audit["effective"] = {"vocab_size": len(vocab), "split_regex": actual_regex}
    return audit


def train_scale(scale_inputs, upstream_dir, python_executable, output_root, runtime, revisions):
    scale = scale_inputs["scale"]
    dirs = output_dirs(output_root, scale)
    cells = {}

    for representation in ("precomposed", "jamo"):
        corpus = scale_inputs["inputs"][representation]
        stage1_key = f"{representation}-bpe"
        stage1_dir = dirs[stage1_key]
        ensure_new_output_dir(stage1_dir)
        command = run_upstream_training(
            python_executable,
            upstream_dir,
            stage1_dir,
            Path(corpus["path"]).parent,
            STAGE1_REGEX,
        )
        validate_stage1_output(stage1_dir, corpus)
        cells[stage1_key] = {
            "representation": representation,
            "compression": "bpe",
            "regex": STAGE1_REGEX,
            "vocab_size": VOCAB_SIZE,
            "corpus": corpus,
            "command": command,
            "artifacts": artifact_audit(stage1_dir, STAGE1_REGEX),
        }

        stage2_key = f"{representation}-superbpe"
        stage2_dir = dirs[stage2_key]
        ensure_new_output_dir(stage2_dir)
        inherited = copy_inherited_merges(stage1_dir / "merges.txt", stage2_dir)
        stage1_meta_sha256 = file_sha256(stage1_dir / "meta.json")
        shutil.copy2(stage1_dir / "meta.json", stage2_dir / "meta.json")
        command = run_upstream_training(
            python_executable,
            upstream_dir,
            stage2_dir,
            Path(corpus["path"]).parent,
            STAGE2_REGEX,
        )
        if file_sha256(stage2_dir / "meta.json") != stage1_meta_sha256:
            raise RuntimeError(f"Stage-2 meta.json drifted from Stage-1 for {representation}")
        cells[stage2_key] = {
            "representation": representation,
            "compression": "superbpe",
            "regex": STAGE2_REGEX,
            "vocab_size": VOCAB_SIZE,
            "corpus": corpus,
            "command": command,
            "inherited_merges": inherited,
            "artifacts": artifact_audit(stage2_dir, STAGE2_REGEX),
        }

    audit = {
        "scale": scale,
        "source_contract": {key: value for key, value in scale_inputs.items() if key != "inputs"},
        "upstream": revisions,
        "runtime": runtime,
        "shared": {
            "vocab_size": VOCAB_SIZE,
            "stage1_regex": STAGE1_REGEX,
            "stage2_regex": STAGE2_REGEX,
            "retained_merge_lines": RETAINED_MERGE_LINES,
            "inherited_merge_rules": RETAINED_MERGE_LINES - 1,
            "pythonhashseed": "0",
        },
        "cells": cells,
    }
    audit_path = output_root / scale / "training_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def main():
    parser = argparse.ArgumentParser(description="Train the implementation-controlled CC-100 Hangul 2x2 with SuperBPE.")
    parser.add_argument("--scale", choices=("100m", "1g"), required=True)
    parser.add_argument("--prepared-metadata", type=Path, default=Path("data/cc100/prepared/metadata.json"))
    parser.add_argument("--upstream-dir", type=Path, default=Path("data/superbpe-upstream"))
    parser.add_argument("--python", type=Path, default=Path("data/superbpe-upstream/.venv/bin/python"))
    parser.add_argument("--output-root", type=Path, default=Path("models/superbpe"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    revisions = validate_upstream(args.upstream_dir)
    scale_inputs = load_scale_inputs(args.prepared_metadata, args.scale)
    runtime = validate_runtime(args.python, args.upstream_dir)
    validation = {"source": scale_inputs, "upstream": revisions, "runtime": runtime}
    if args.validate_only:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return

    audit = train_scale(
        scale_inputs, args.upstream_dir.resolve(), args.python.resolve(), args.output_root, runtime, revisions
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
