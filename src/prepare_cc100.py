import argparse
import hashlib
import json
import lzma
from contextlib import ExitStack
from pathlib import Path

CC100_KO_URL = "https://data.statmt.org/cc-100/ko.txt.xz"
DEFAULT_BUDGETS = {
    "100m": 100 * 1024 * 1024,
    "1g": 1024 * 1024 * 1024,
}
JAMO_TSV_SHA256 = "94947cc5bc7c5d2eb63f1b743ede3d27191c5dcf2d73c40de7ba82c8c9854a86"
DOCUMENT_SEPARATOR = b"\n\n"


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_xz(path):
    decoded_bytes = 0
    with lzma.open(path, "rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            decoded_bytes += len(chunk)
    return decoded_bytes


def load_jamo_translation(path):
    translation = {}
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 2:
                raise ValueError(f"Malformed Jamo TSV line {line_number}: expected two tab-separated fields")
            source_hex, target_hexes = fields
            source_codepoint = int(source_hex, 16)
            if source_codepoint in translation:
                raise ValueError(f"Duplicate Jamo TSV source code point on line {line_number}: {source_hex}")
            translation[source_codepoint] = "".join(chr(int(part, 16)) for part in target_hexes.split())

    expected = set(range(0xAC00, 0xD7A4))
    if set(translation) != expected:
        raise ValueError("Jamo TSV must map every modern precomposed Hangul syllable U+AC00-U+D7A3 exactly once")
    return translation


def iter_documents(source, chunk_size=1024 * 1024):
    buffer = bytearray()
    while chunk := source.read(chunk_size):
        buffer.extend(chunk)
        while True:
            boundary = buffer.find(DOCUMENT_SEPARATOR)
            if boundary < 0:
                break
            end = boundary + len(DOCUMENT_SEPARATOR)
            document = bytes(buffer[:end])
            del buffer[:end]
            if document != DOCUMENT_SEPARATOR:
                yield document

    if buffer.strip(b"\n"):
        yield bytes(buffer)


def _new_slice_state(output_dir, scale, budget_bytes):
    scale_dir = output_dir / scale
    source_dir = scale_dir / "precomposed"
    jamo_dir = scale_dir / "jamo"
    source_dir.mkdir(parents=True, exist_ok=True)
    jamo_dir.mkdir(parents=True, exist_ok=True)
    return {
        "budget_bytes": budget_bytes,
        "source_path": source_dir / "train.txt",
        "jamo_path": jamo_dir / "train.txt",
        "source_digest": hashlib.sha256(),
        "jamo_digest": hashlib.sha256(),
        "documents": 0,
        "paragraphs": 0,
        "source_bytes": 0,
        "source_characters": 0,
        "jamo_bytes": 0,
        "jamo_characters": 0,
        "first_document_sha256": None,
        "last_document_sha256": None,
        "stopped_before_document_bytes": None,
    }


def prepare_slices(archive_path, output_dir, jamo_translation, budgets=DEFAULT_BUDGETS):
    if not budgets or any(budget <= 0 for budget in budgets.values()):
        raise ValueError("All source-byte budgets must be positive")

    ordered_scales = [scale for scale, _ in sorted(budgets.items(), key=lambda item: item[1])]
    states = {scale: _new_slice_state(output_dir, scale, budgets[scale]) for scale in ordered_scales}
    active_scales = set(ordered_scales)

    with ExitStack() as stack:
        source_handles = {
            scale: stack.enter_context(states[scale]["source_path"].open("wb")) for scale in ordered_scales
        }
        jamo_handles = {scale: stack.enter_context(states[scale]["jamo_path"].open("wb")) for scale in ordered_scales}
        archive = stack.enter_context(lzma.open(archive_path, "rb"))

        for document in iter_documents(archive):
            fitting_scales = []
            for scale in list(active_scales):
                state = states[scale]
                if state["source_bytes"] + len(document) > state["budget_bytes"]:
                    state["stopped_before_document_bytes"] = len(document)
                    active_scales.remove(scale)
                else:
                    fitting_scales.append(scale)

            if not fitting_scales:
                if not active_scales:
                    break
                continue

            source_text = document.decode("utf-8")
            jamo_text = source_text.translate(jamo_translation)
            jamo_bytes = jamo_text.encode("utf-8")
            document_sha256 = hashlib.sha256(document).hexdigest()
            paragraphs = sum(1 for line in source_text.split("\n") if line)

            for scale in fitting_scales:
                state = states[scale]
                source_handles[scale].write(document)
                jamo_handles[scale].write(jamo_bytes)
                state["source_digest"].update(document)
                state["jamo_digest"].update(jamo_bytes)
                state["documents"] += 1
                state["paragraphs"] += paragraphs
                state["source_bytes"] += len(document)
                state["source_characters"] += len(source_text)
                state["jamo_bytes"] += len(jamo_bytes)
                state["jamo_characters"] += len(jamo_text)
                state["first_document_sha256"] = state["first_document_sha256"] or document_sha256
                state["last_document_sha256"] = document_sha256

            if not active_scales:
                break

    result = {}
    for scale in ordered_scales:
        state = states[scale]
        if state["source_path"].stat().st_size != state["source_bytes"]:
            raise RuntimeError(f"{scale} precomposed byte count does not match the written file")
        if state["jamo_path"].stat().st_size != state["jamo_bytes"]:
            raise RuntimeError(f"{scale} Jamo byte count does not match the written file")
        result[scale] = {
            "budget_bytes": state["budget_bytes"],
            "documents": state["documents"],
            "paragraphs": state["paragraphs"],
            "first_document_sha256": state["first_document_sha256"],
            "last_document_sha256": state["last_document_sha256"],
            "stopped_before_document_bytes": state["stopped_before_document_bytes"],
            "source": {
                "path": str(state["source_path"]),
                "bytes": state["source_bytes"],
                "characters": state["source_characters"],
                "sha256": state["source_digest"].hexdigest(),
            },
            "jamo": {
                "path": str(state["jamo_path"]),
                "bytes": state["jamo_bytes"],
                "characters": state["jamo_characters"],
                "sha256": state["jamo_digest"].hexdigest(),
            },
        }
    return result


def audit_jamo_tsv(path):
    digest = file_sha256(path)
    if digest != JAMO_TSV_SHA256:
        raise RuntimeError(f"Unexpected Jamo TSV SHA-256: {digest}")
    translation = load_jamo_translation(path)
    return translation, {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest,
        "entries": len(translation),
    }


def audit_archive(path):
    return {
        "url": CC100_KO_URL,
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "decoded_bytes": verify_xz(path),
        "xz_integrity_verified": True,
        "document_boundary": "double-newline",
        "paragraph_boundary": "single-newline",
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare deterministic CC-100 Korean source and Jamo training slices.")
    parser.add_argument("--input", type=Path, default=Path("data/cc100/ko.txt.xz"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/cc100/prepared"))
    parser.add_argument("--jamo-tsv", type=Path, default=Path("data/korean_hangul_jamo.tsv"))
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"CC-100 Korean archive not found: {args.input}")

    translation, jamo_audit = audit_jamo_tsv(args.jamo_tsv)
    archive_audit = audit_archive(args.input)
    slices = prepare_slices(args.input, args.output_dir, translation)
    metadata = {
        "source": archive_audit,
        "jamo_tsv": jamo_audit,
        "slices": slices,
    }

    metadata_path = args.output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
