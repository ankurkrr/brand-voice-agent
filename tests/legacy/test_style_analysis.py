# tests/unit/test_style_analysis.py

from core.voice.style_analysis import (
    avg_sentence_length,
    sentence_tokenize,
    style_metrics_from_documents,
)
from langchain_core.documents import Document

def test_sentence_tokenize():
    text = "This is one sentence. This is two!"
    sents = sentence_tokenize(text)
    assert len(sents) == 2

def test_avg_sentence_length():
    text = "Hello world. This is a test sentence."
    length = avg_sentence_length(text)
    assert length > 1   # not zero, correct behavior

def test_style_metrics_from_documents():
    docs = [
        Document(page_content="This is a test. It should work well!"),
        Document(page_content="Another example sentence for style metrics."),
    ]

    metrics = style_metrics_from_documents(docs)

    assert "avg_sentence_length" in metrics
    assert "vocab_profile" in metrics
    assert "punct_profile" in metrics
    assert metrics["sentiment_estimate"] == "neutral"
