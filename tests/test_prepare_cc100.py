import io
import lzma
from pathlib import Path

from prepare_cc100 import iter_documents, load_jamo_translation, prepare_slices, verify_xz

REPO_ROOT = Path(__file__).parents[1]
JAMO_TSV = REPO_ROOT / "data/korean_hangul_jamo.tsv"


def write_xz(path, data):
    with lzma.open(path, "wb") as target:
        target.write(data)


def test_iter_documents_preserves_double_newline_boundaries():
    corpus = "첫 문단\n둘째 문단\n\n다른 문서\n\n".encode()

    assert list(iter_documents(io.BytesIO(corpus), chunk_size=7)) == [
        "첫 문단\n둘째 문단\n\n".encode(),
        "다른 문서\n\n".encode(),
    ]


def test_prepare_slices_uses_maximal_whole_document_prefixes(tmp_path):
    documents = [
        "가\n첫 문서\n\n".encode(),
        "각\n둘째 문서\n\n".encode(),
        "나\n셋째 문서\n\n".encode(),
    ]
    archive = tmp_path / "ko.txt.xz"
    write_xz(archive, b"".join(documents))
    translation = load_jamo_translation(JAMO_TSV)
    budgets = {
        "small": len(documents[0]) + len(documents[1]) - 1,
        "large": sum(map(len, documents)) - 1,
    }

    result = prepare_slices(archive, tmp_path / "prepared", translation, budgets)

    small_source = documents[0]
    large_source = b"".join(documents[:2])
    assert (tmp_path / "prepared/small/precomposed/train.txt").read_bytes() == small_source
    assert (tmp_path / "prepared/large/precomposed/train.txt").read_bytes() == large_source
    assert (tmp_path / "prepared/small/jamo/train.txt").read_text(encoding="utf-8") == small_source.decode().translate(
        translation
    )
    assert (tmp_path / "prepared/large/jamo/train.txt").read_text(encoding="utf-8") == large_source.decode().translate(
        translation
    )
    assert result["small"]["documents"] == 1
    assert result["large"]["documents"] == 2
    assert result["small"]["stopped_before_document_bytes"] == len(documents[1])
    assert result["large"]["stopped_before_document_bytes"] == len(documents[2])
    assert result["small"]["source"]["bytes"] == len(small_source)
    assert result["large"]["source"]["bytes"] == len(large_source)


def test_verify_xz_reads_complete_stream(tmp_path):
    payload = ("한글 corpus\n\n" * 10).encode()
    archive = tmp_path / "sample.txt.xz"
    write_xz(archive, payload)

    assert verify_xz(archive) == len(payload)
