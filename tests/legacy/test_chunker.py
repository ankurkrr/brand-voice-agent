# tests/unit/test_chunker.py
from lib.text.chunker import chunk_documents
from langchain_core.documents import Document

def test_chunk_documents():
    docs = [Document(page_content="This is a sentence. Another sentence.")]
    chunks = chunk_documents(docs, chunk_size=50, chunk_overlap=10)
    assert isinstance(chunks, list)
    assert all(hasattr(c, "page_content") for c in chunks)
