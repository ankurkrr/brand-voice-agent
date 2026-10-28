# tests/unit/test_preprocess.py
from lib.text.preprocess import clean_text, join_documents
from langchain_core.documents import Document

def test_clean_text():
    dirty = "Hello   world.\n\n\nPage 1 of 5"
    cleaned = clean_text(dirty)
    assert "Page" not in cleaned   # footer removed
    assert "  " not in cleaned      # double spaces removed

def test_join_documents():
    docs = [Document(page_content="A"), Document(page_content="B")]
    text = join_documents(docs)
    assert "A" in text and "B" in text
