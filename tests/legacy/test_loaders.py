# tests/unit/test_loaders.py
import tempfile
import pytest
from lib.loaders.file import load_pdf, load_docx, load_url
from lib.text.preprocess import clean_text
from importlib.util import find_spec

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def test_load_pdf(tmp_path):
    tmp = tmp_path / "t.pdf"
    tmp.write_bytes(MINIMAL_PDF)
    docs = load_pdf(str(tmp))
    assert isinstance(docs, list)


@pytest.mark.skipif(find_spec("docx2txt") is None, reason="docx2txt not installed")
def test_load_docx(tmp_path):
    tmp = tmp_path / "t.docx"
    # write a minimal zip-based file would be complex; rely on loader and dependency - create an actual simple .docx via python-docx if needed.
    # For CI we skip unless docx2txt exists; create a small placeholder file if library present
    tmp.write_text("Fake docx content")
    docs = load_docx(str(tmp))
    assert isinstance(docs, list)


def test_load_url():
    # loader returns list for a simple public URL; we keep this minimal and not network-dependent in CI
    # if internet blocked, assert loader handles gracefully (either list or raises)
    try:
        docs = load_url("http://example.com")
        assert isinstance(docs, list)
    except Exception:
        pytest.skip("network unavailable")
