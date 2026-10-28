# tests/unit/test_example_selector.py

import pytest
from unittest.mock import patch, MagicMock
from core.voice.example_selector import select_best_examples

@pytest.mark.asyncio
async def test_select_best_examples():
    mock_docs = [
        MagicMock(page_content="Example A text here"),
        MagicMock(page_content="Example B text here"),
        MagicMock(page_content="Example C text here"),
    ]

    with patch("core.voice.example_selector.Chroma") as mock_chroma:
        instance = mock_chroma.return_value
        instance.similarity_search.return_value = mock_docs

        result = await select_best_examples("brand_test", top_k=3)

    assert len(result) == 3
    assert isinstance(result[0]["text"], str)
    assert result[0]["text"].startswith("Example")
