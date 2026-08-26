import json

import pytest

import train_superbpe
from train_superbpe import (
    RETAINED_MERGE_LINES,
    STAGE1_REGEX,
    artifact_audit,
    copy_inherited_merges,
    file_sha256,
    load_scale_inputs,
    output_dirs,
    run_upstream_training,
    validate_stage1_output,
)


def write_prepared_metadata(tmp_path):
    prepared = tmp_path / "prepared/100m"
    precomposed = prepared / "precomposed/train.txt"
    jamo = prepared / "jamo/train.txt"
    precomposed.parent.mkdir(parents=True)
    jamo.parent.mkdir(parents=True)
    precomposed.write_text("한글 문서\n\n", encoding="utf-8")
    jamo.write_text("한글 문서\n\n", encoding="utf-8")

    metadata = {
        "slices": {
            "100m": {
                "budget_bytes": 100 * 1024 * 1024,
                "documents": 1,
                "first_document_sha256": "first",
                "last_document_sha256": "last",
                "source": {
                    "path": str(precomposed),
                    "bytes": precomposed.stat().st_size,
                    "sha256": file_sha256(precomposed),
                },
                "jamo": {
                    "path": str(jamo),
                    "bytes": jamo.stat().st_size,
                    "sha256": file_sha256(jamo),
                },
            }
        }
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata_path, precomposed, jamo


def test_load_scale_inputs_verifies_dedicated_corpus_dirs(tmp_path):
    metadata_path, precomposed, jamo = write_prepared_metadata(tmp_path)

    result = load_scale_inputs(metadata_path, "100m")

    assert result["source_documents"] == 1
    assert result["inputs"]["precomposed"]["path"] == str(precomposed.resolve())
    assert result["inputs"]["jamo"]["path"] == str(jamo.resolve())


def test_load_scale_inputs_rejects_extra_upstream_eligible_text(tmp_path):
    metadata_path, precomposed, _ = write_prepared_metadata(tmp_path)
    (precomposed.parent / "other.txt").write_text("오염", encoding="utf-8")

    with pytest.raises(RuntimeError, match="exactly one upstream-eligible"):
        load_scale_inputs(metadata_path, "100m")


def test_load_scale_inputs_rejects_content_drift(tmp_path):
    metadata_path, precomposed, _ = write_prepared_metadata(tmp_path)
    precomposed.write_text("변경됨\n\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="mismatch"):
        load_scale_inputs(metadata_path, "100m")


def test_copy_inherited_merges_keeps_header_and_exact_rule_budget(tmp_path):
    stage1 = tmp_path / "stage1-merges.txt"
    lines = ["#version: 0.2\n"] + [f"a{i} b{i}\n" for i in range(RETAINED_MERGE_LINES + 10)]
    stage1.write_text("".join(lines), encoding="utf-8")
    stage2 = tmp_path / "stage2"

    audit = copy_inherited_merges(stage1, stage2)

    inherited = (stage2 / "inherited_merges.txt").read_text(encoding="utf-8").splitlines()
    seed = (stage2 / "merges.txt").read_text(encoding="utf-8").splitlines()
    assert len(inherited) == RETAINED_MERGE_LINES
    assert inherited == seed
    assert audit["retained_lines"] == RETAINED_MERGE_LINES
    assert audit["inherited_merge_rules"] == RETAINED_MERGE_LINES - 1


def test_run_upstream_training_uses_entire_prepared_view(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(train_superbpe.subprocess, "run", fake_run)
    python_executable = tmp_path / "venv/bin/python"
    upstream_dir = tmp_path / "upstream"
    output_dir = tmp_path / "model"
    corpus_dir = tmp_path / "corpus"

    command = run_upstream_training(python_executable, upstream_dir, output_dir, corpus_dir, STAGE1_REGEX)

    assert calls
    assert "--num_bytes" not in command
    assert command[command.index("--vocab_size") + 1] == "32000"
    assert command[command.index("--corpus_dir") + 1] == str(corpus_dir.resolve())
    assert calls[0][1]["cwd"] == upstream_dir
    assert calls[0][1]["env"]["PYTHONHASHSEED"] == "0"


def test_validate_stage1_output_requires_exact_prepared_file(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    corpus = tmp_path / "corpus/train.txt"
    corpus.parent.mkdir()
    corpus.write_text("한글\n", encoding="utf-8")
    for name in ("merges.txt", "vocab.json", "tokenizer.json"):
        (model / name).write_text("x", encoding="utf-8")
    (model / "meta.json").write_text(
        json.dumps({"train_files": [str(corpus.resolve())], "total_bytes": corpus.stat().st_size}),
        encoding="utf-8",
    )

    validate_stage1_output(
        model,
        {"path": str(corpus.resolve()), "bytes": corpus.stat().st_size, "sha256": file_sha256(corpus)},
    )

    (model / "meta.json").write_text(
        json.dumps({"train_files": [str(corpus.resolve()), "extra.txt"], "total_bytes": corpus.stat().st_size}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="exactly the prepared corpus"):
        validate_stage1_output(
            model,
            {"path": str(corpus.resolve()), "bytes": corpus.stat().st_size, "sha256": file_sha256(corpus)},
        )


def test_output_dirs_are_scale_scoped(tmp_path):
    dirs = output_dirs(tmp_path, "100m")

    assert dirs["precomposed-bpe"] == tmp_path / "100m/precomposed-bpe-32k"
    assert dirs["jamo-superbpe"] == tmp_path / "100m/jamo-superbpe-32k"


def test_artifact_audit_checks_effective_vocab_and_regex(monkeypatch, tmp_path):
    monkeypatch.setattr(train_superbpe, "VOCAB_SIZE", 2)
    model = tmp_path / "model"
    model.mkdir()
    (model / "meta.json").write_text("{}", encoding="utf-8")
    (model / "merges.txt").write_text("#version: 0.2\na b\n", encoding="utf-8")
    (model / "vocab.json").write_text(json.dumps({"a": 0, "b": 1}), encoding="utf-8")
    (model / "tokenizer.json").write_text(
        json.dumps(
            {
                "pre_tokenizer": {
                    "type": "Sequence",
                    "pretokenizers": [
                        {"type": "Split", "pattern": {"Regex": "expected"}},
                        {"type": "ByteLevel"},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    audit = artifact_audit(model, "expected")

    assert audit["effective"] == {"vocab_size": 2, "split_regex": "expected"}
    with pytest.raises(RuntimeError, match="Split regex mismatch"):
        artifact_audit(model, "wrong")
