from hangul_metrics import summarize_vocab


def test_summarize_vocab_reports_raw_and_recomposed_hangul_structure():
    stats = summarize_vocab(
        [
            "가".encode(),
            "가".encode(),
            "한글".encode(),
            b"\xff",
        ]
    )

    assert stats["total"] == 4
    assert stats["atomic"] == 1
    assert stats["multi"] == 0
    assert stats["jamo"] == 2
    assert stats["fragments"] == 1
    assert stats["recomposed_atomic"] == 1
    assert stats["recomposed_multi"] == 1
    assert stats["max_recomposed_syllables"] == 2
