import pytest

import benchmark_corpus
from benchmark_corpus import build_counter, corpus_metrics, distribution_summary, load_flores_units
from prepare_flores import prepare_flores


class CharacterCounter:
    def count(self, text):
        return len(text), 0


def test_distribution_summary_uses_deterministic_linear_percentiles():
    summary = distribution_summary([1, 2, 3, 4])

    assert summary == {
        "count": 4,
        "mean": 2.5,
        "min": 1,
        "p25": 1.75,
        "median": 2.5,
        "p75": 3.25,
        "p95": 3.85,
        "max": 4,
    }


def test_corpus_metrics_pairs_nfc_and_nfd_from_same_units():
    metrics = corpus_metrics(CharacterCounter(), ["한글", "abc"])

    assert metrics["sentences"] == 2
    assert metrics["characters"] == 5
    assert metrics["utf8_bytes"] == 9
    assert metrics["hangul_syllables"] == 2
    assert metrics["nfc_tokens"] == 5
    assert metrics["nfd_tokens"] == 9
    assert metrics["nfd_nfc_ratio"] == 1.8
    assert metrics["bytes_per_token"] == 1.8
    assert metrics["tokens_per_hangul_syllable"] == 2.5


def test_load_flores_units_validates_prepared_identity(tmp_path):
    source = tmp_path / "kor_Hang.jsonl"
    source.write_text(
        "\n".join(
            [
                '{"id":"1","iso_639_3":"kor","iso_15924":"Hang","split":"devtest","text":"첫 문장"}',
                '{"id":"2","iso_639_3":"kor","iso_15924":"Hang","split":"devtest","text":"둘째 문장"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "prepared"
    prepare_flores(source, output_dir, revision="a" * 40, expected_rows=2)

    units, identity = load_flores_units(output_dir / "kor_Hang_devtest.txt", output_dir / "metadata.json")

    assert units == ["첫 문장", "둘째 문장"]
    assert identity["rows"] == 2
    assert identity["revision"] == "a" * 40


def test_load_flores_units_rejects_drift(tmp_path):
    source = tmp_path / "kor_Hang.jsonl"
    source.write_text(
        '{"id":"1","iso_639_3":"kor","iso_15924":"Hang","split":"devtest","text":"문장"}\n',
        encoding="utf-8",
    )
    output_dir = tmp_path / "prepared"
    prepare_flores(source, output_dir, revision="b" * 40, expected_rows=1)
    prepared = output_dir / "kor_Hang_devtest.txt"
    prepared.write_text("변조됨\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="differs|mismatch"):
        load_flores_units(prepared, output_dir / "metadata.json")


def test_build_counter_allows_native_hf_for_production(monkeypatch, tmp_path):
    sentinel = object()
    monkeypatch.setattr(benchmark_corpus, "HFJsonCounter", lambda *args, **kwargs: sentinel)

    counter, contract = build_counter("hf-json", "tokenizer.json", "native", tmp_path / "unused.tsv")

    assert counter is sentinel
    assert contract == {"mode": "native"}


def test_build_counter_rejects_modified_jamo_mapping(tmp_path):
    bad_tsv = tmp_path / "jamo.tsv"
    bad_tsv.write_text("AC00\t1100 1161\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Unexpected Jamo TSV SHA-256"):
        build_counter("hf-json", "tokenizer.json", "jamo", bad_tsv)
