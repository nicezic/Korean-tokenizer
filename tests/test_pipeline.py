import pytest

from extract_wikipedia import clean_wikitext
from split_corpus import is_test_document, iter_documents
from train_sentencepiece import assert_fair_configs, assert_normalization_contract, auxiliary_name, common_config


def test_clean_wikitext_strips_markup_and_chunks():
    text = "'''한글'''은 [[문자|조합형 문자]]다. " + "가나다라마바사 " * 10
    lines = list(clean_wikitext(text, max_chars=24))

    assert lines
    assert all(len(line) <= 24 for line in lines)
    assert "'''" not in " ".join(lines)
    assert "[[" not in " ".join(lines)
    assert "조합형 문자" in " ".join(lines)
    assert list(clean_wikitext("한글", max_chars=24)) == ["한글"]


def test_iter_documents_preserves_blank_line_boundaries(tmp_path):
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("첫 문장\n둘째 문장\n\n다른 문서\n\n", encoding="utf-8")

    assert list(iter_documents(corpus)) == [["첫 문장", "둘째 문장"], ["다른 문서"]]


def test_content_hash_split_is_deterministic():
    document = ["동일한 문서는 항상 같은 split으로 간다."]

    assert is_test_document(document, 500) == is_test_document(document, 500)


def test_training_config_enables_byte_fallback_and_fairness(tmp_path):
    common = common_config(tmp_path / "train.txt", 32_000)
    baseline = {**common, "model_prefix": "baseline", "normalization_rule_name": "identity"}
    jamo = {**common, "model_prefix": "jamo", "normalization_rule_tsv": "jamo.tsv"}

    assert common["byte_fallback"] is True
    assert_fair_configs(baseline, jamo)

    broken = {**jamo, "character_coverage": 0.9995}
    with pytest.raises(RuntimeError):
        assert_fair_configs(baseline, broken)


def test_normalization_contract_and_auxiliary_name():
    baseline = {"nfc_normalized": "▁한", "nfd_normalized": "▁한"}
    jamo = {"nfc_normalized": "▁한", "nfd_normalized": "▁한"}

    assert_normalization_contract(baseline, jamo)
    assert auxiliary_name(24_000) == "jamo-24k"

    with pytest.raises(RuntimeError):
        assert_normalization_contract(baseline, {**jamo, "nfd_normalized": "▁한"})
