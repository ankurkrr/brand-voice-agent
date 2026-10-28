import pytest
from unittest.mock import AsyncMock
from core.agents.v1.agent1_voice import run_agent1
from langchain_core.documents import Document

@pytest.mark.asyncio
@pytest.mark.v1
async def test_run_agent1_v1_payload_structure(mocker, mock_llm):
    # Setup
    mocker.patch("core.agents.v1.agent1_voice.ChatGoogleGenerativeAI", return_value=mock_llm)
    mocker.patch("core.agents.v1.agent1_voice.extract_rules_from_text", new_callable=AsyncMock, return_value={
        "dos": ["Use active voice"],
        "donts": ["Use passive voice"],
        "tone": {"primary": "Expert"},
        "forbidden_phrases": [],
        "preferred_vocabulary": []
    })
    
    docs = [Document(page_content="Brand guidelines text")]
    
    # Execute
    result = await run_agent1(
        source_docs=docs,
        source_text_for_rules="Brand guidelines text",
        collection_name="test_col"
    )
    
    # Assert Output Contract
    assert result["success"] is True
    assert result["version"] == 1
    assert "raw_json" in result
    
    golden_record = result["raw_json"]
    assert "expert" in golden_record["system_prompt"].lower()
    assert golden_record["explicit_rules"]["dos"] == ["Use active voice"]
    assert golden_record["version"] == 1

@pytest.mark.asyncio
@pytest.mark.v1
async def test_run_agent1_v1_handles_regeneration(mocker, mock_llm):
    # Setup
    mocker.patch("core.agents.v1.agent1_voice.ChatGoogleGenerativeAI", return_value=mock_llm)
    
    # Specifically mock the file read for regeneration prefix so tests pass without real files
    mocker.patch("pathlib.Path.read_text", return_value="PREFIX: ")
    
    mock_extract = mocker.patch("core.agents.v1.agent1_voice.extract_rules_from_text", new_callable=AsyncMock, return_value={})
    
    docs = [Document(page_content="Test")]
    
    # Execute
    await run_agent1(
        source_docs=docs,
        source_text_for_rules="Original text",
        collection_name="test_col",
        regenerate=True
    )
    
    # Assert
    # The variation prefix should have been prepended to the text
    args, _ = mock_extract.call_args
    assert args[0] == "PREFIX: Original text"
