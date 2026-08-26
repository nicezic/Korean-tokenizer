import json

import pytest

from prepare_flores import load_devtest, prepare_flores


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def korean_row(row_id, text, split="devtest"):
    return {
        "id": row_id,
        "iso_639_3": "kor",
        "iso_15924": "Hang",
        "glottocode": "kore1280",
        "variant": "",
        "text": text,
        "split": split,
    }


def test_prepare_flores_preserves_order_and_records_identity(tmp_path):
    source = tmp_path / "kor_Hang.jsonl"
    rows = [korean_row("2", "둘째 문장"), korean_row("1", "첫째라는 이름이지만 두 번째 행")]
    write_jsonl(source, rows)

    metadata = prepare_flores(source, tmp_path / "prepared", "deadbeef", expected_rows=2)

    output = tmp_path / "prepared/kor_Hang_devtest.txt"
    assert output.read_text(encoding="utf-8") == "둘째 문장\n첫째라는 이름이지만 두 번째 행\n"
    assert metadata["revision"] == "deadbeef"
    assert metadata["rows"] == 2
    assert metadata["first_id"] == "2"
    assert metadata["last_id"] == "1"
    assert metadata["prepared"]["bytes"] == output.stat().st_size


def test_load_devtest_rejects_wrong_language_or_split(tmp_path):
    source = tmp_path / "wrong.jsonl"
    write_jsonl(source, [korean_row("1", "문장", split="dev")])

    with pytest.raises(ValueError, match="split=devtest"):
        load_devtest(source, expected_rows=1)


def test_load_devtest_rejects_duplicate_ids(tmp_path):
    source = tmp_path / "duplicate.jsonl"
    write_jsonl(source, [korean_row("1", "하나"), korean_row("1", "둘")])

    with pytest.raises(ValueError, match="Duplicate FLORES\\+ id"):
        load_devtest(source, expected_rows=2)


def test_prepare_flores_requires_immutable_revision(tmp_path):
    source = tmp_path / "kor_Hang.jsonl"
    write_jsonl(source, [korean_row("1", "문장")])

    with pytest.raises(ValueError, match="immutable revision"):
        prepare_flores(source, tmp_path / "prepared", "main", expected_rows=1)
