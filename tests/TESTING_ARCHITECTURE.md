# Marketing Agent Test Architecture Guide

This document outlines the rebuilt, enterprise-grade `pytest` architecture for the versioned multi-agent AI marketing system.

## 1. Directory Structure

A strict separation between unit and integration tests is required to enforce boundary isolation and ensure that unit tests never hit real DBs, LLMs, or Web Search APIs.

```text
tests/
├── conftest.py                   # Global fixtures and mock patches
├── pytest.ini                    # Pytest configuration
├── unit/
│   ├── conftest.py               # Unit-specific fixtures (strict mocking)
│   ├── agents/
│   │   ├── v1/
│   │   │   ├── test_agent1_voice.py
│   │   │   ├── test_agent2_ideation.py
│   │   │   └── test_agent3_execution.py
│   │   └── v2/
│   │       ├── test_agent1_voice.py
│   │       ├── test_agent2_ideation.py
│   │       └── test_agent3_execution.py
│   ├── orchestration/
│   │   └── test_version_router.py
│   ├── voice/
│   │   └── test_dimensional_scorer.py
│   └── ideation/
│       └── test_brief_builder.py
├── integration/                  # Hits mock-DBs but REAL agent logic flows
│   ├── conftest.py               # Spawns testcontainers/sqlite for DB
│   └── test_v1_pipeline.py
├── e2e/                          # Full stack, uses real LLM/DB (skipped by default)
│   └── test_full_agent_workflow.py
└── fixtures/
    ├── mocks/                    # Reusable mock classes
    │   ├── mock_llm.py
    │   ├── mock_repos.py
    │   └── mock_tavily.py
    └── payloads/                 # Static JSON payloads for testing
        ├── v1_golden_record.json
        ├── v2_persona_record.json
        └── raw_brand_guidelines.txt
```

## 2. Pytest Configuration (`pytest.ini`)

Enforce strict markers and async configurations.

```ini
[pytest]
asyncio_mode = auto
addopts = --strict-markers -v --cov=core --cov-report=term-missing
markers =
    unit: Fast tests that mock all external limits (DB, API, LLMs)
    integration: Tests that require a database connection (SQLite/Testcontainers)
    e2e: Tests that hit real LLM APIs (skipped by default)
    v1: Tests targeting V1 specific logic
    v2: Tests targeting V2 specific logic
```

## 3. Mock Patterns & Base Fixtures (`tests/conftest.py`)

Using `pytest-asyncio` and `unittest.mock.AsyncMock` is critical. We use dependency injection for the LLM to easily mock it.

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

# --- Repositories Mock ---
@pytest.fixture
def mock_voice_profiles_repo(mocker):
    repo = mocker.patch("data.repos.voice_profiles.VoiceProfilesRepo")
    repo.get_active_profile = AsyncMock()
    repo.save_profile = AsyncMock()
    repo.update_human_profile = AsyncMock()
    return repo

@pytest.fixture
def mock_content_briefs_repo(mocker):
    repo = mocker.patch("data.repos.content_briefs.ContentBriefsRepo")
    repo.fetch_content_briefs_by_brand_id = AsyncMock(return_value=[])
    repo.insert_content_brief = AsyncMock(return_value={"id": "mock_brief_id"})
    return repo

@pytest.fixture
def mock_voice_personas_repo(mocker):
    repo = mocker.patch("data.repos.voice_personas.VoicePersonasRepo")
    repo.create_persona = AsyncMock()
    repo.get_persona = AsyncMock()
    return repo

# --- LLM Mock Pattern ---
@pytest.fixture
def mock_llm():
    """
    Mocks standard LangChain LLM responses.
    Allows testing Agent extraction logic without hitting Google.
    """
    class MockResponse:
        def __init__(self, content):
            self.content = content
            
        def dict(self):
            # For PydanticOutputParser mocks
            import json
            return json.loads(self.content)

    mock_llm_instance = AsyncMock()
    
    # Configure default successful response
    mock_llm_instance.ainvoke.return_value = MockResponse(
        content='{"dos": ["Be kind"], "donts": ["Be rude"], "tone": {"primary": "Professional"}}'
    )
    return mock_llm_instance

# --- Vector / Search Mocks ---
@pytest.fixture
def mock_web_signals(mocker):
    return mocker.patch(
        "core.ideation.web_research.gather_web_signals",
        new_callable=AsyncMock,
        return_value={"fingerprint": "hash123", "trends": ["AI adoption"]}
    )

@pytest.fixture
def mock_chroma(mocker):
    mocker.patch("core.storage.vector.upsert_chunks_to_chroma", return_value=True)
    mocker.patch("core.storage.vector.fetch_chunks_from_chroma", return_value=["mock_doc_chunk"])
```

## 4. Example Test Templates

### Agent 1 V1 (`tests/unit/agents/v1/test_agent1_voice.py`)
Validates extraction and V1 payload structure.

```python
import pytest
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
        "tone": {"primary": "Expert"}
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
```

### Agent 1 V2 (`tests/unit/agents/v2/test_agent1_voice.py`)
Validates Brand ID enforcement, Dimensional scoring dependencies, and Persona creation.

```python
import pytest
from core.agents.v2.agent1_voice import run_agent1

@pytest.mark.asyncio
@pytest.mark.v2
async def test_agent1_v2_enforces_brand_id():
    """Architectural Invariant: Agent 1 V2 MUST require a brand_id."""
    v1_mock_profile = {
        "system_prompt": "Mock prompt",
        "explicit_rules": {}
        # Notice: No brand_id
    }
    
    with pytest.raises(ValueError, match="requires brand_id to create persona"):
        await run_agent1(parent_profile=v1_mock_profile)


@pytest.mark.asyncio
@pytest.mark.v2
async def test_agent1_v2_persona_persistence(mocker, mock_voice_personas_repo, mock_llm):
    # Setup Mock Pydantic Chain output
    mocker.patch("core.agents.v2.agent1_voice.ChatGoogleGenerativeAI", return_value=mock_llm)
    
    class MockDataObj:
        def dict(self):
            return {
                "refined_explicit_rules": {"tone": {"primary": "Witty"}, "dos": [], "donts": []},
                "implicit_rules": {},
            }
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MockDataObj()
    
    # Patch the chain creation (Requires refactoring see section 5)
    # Alternatively, mock the parser wrapper.
    ...
```

### Agent 2 Boundary Enforcement (`tests/unit/agents/test_agent2_boundaries.py`)
Validates that Agent 2 strictly rejects style/tone leakage.

```python
import pytest
from core.agents.agent2 import run_agent2_ideation

@pytest.mark.asyncio
async def test_agent2_rejects_tone_leakage():
    """Architectural Invariant: Agent 2 must NOT receive voice/tone data."""
    with pytest.raises(ValueError, match="BOUNDARY VIOLATION"):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech",
            tone="Professional"  # ILLEGAL KWARG!
        )

    with pytest.raises(ValueError, match="BOUNDARY VIOLATION"):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech",
            dos=["Be friendly"]  # ILLEGAL KWARG!
        )
```

### Version Router Isolation (`tests/unit/orchestration/test_version_router.py`)

```python
import pytest
from core.orchestration.version_router import route_execution

def test_version_router_directs_correctly(mocker):
    v1_mock = mocker.patch("core.agents.v1.agent3_execution.run_agent3")
    v2_mock = mocker.patch("core.agents.v2.agent3_execution.run_agent3")
    
    # Test V1 route
    route_execution(version="v1", task="generation", request_data={"brand_id": "test"})
    v1_mock.assert_called_once()
    v2_mock.assert_not_called()
    
    # Test V2 route
    v1_mock.reset_mock()
    route_execution(version="v2", task="generation", request_data={"brand_id": "test"})
    v2_mock.assert_called_once()
    v1_mock.assert_not_called()
```

### Deterministic Fingerprint Reuse (`tests/unit/agents/test_agent2_ideation.py`)

```python
import pytest
from core.agents.agent2 import run_agent2_ideation

@pytest.mark.asyncio
async def test_agent2_reuses_brief_by_fingerprint(
    mock_content_briefs_repo, mock_web_signals, mocker
):
    # Setup DB to return an existing brief matching fingerprint "hash123"
    mock_content_briefs_repo.fetch_content_briefs_by_brand_id.return_value = [
        {"brief_id": "existing_brief", "content_brief_data": {"fingerprint": "hash123"}}
    ]
    
    # Mock LLM Builder (should NOT be called)
    mock_build = mocker.patch("core.agents.agent2.build_content_brief", new_callable=AsyncMock)
    
    result = await run_agent2_ideation(
        brand_id="123",
        topic="AI in 2026",
        skip_brand_check=True
    )
    
    assert result["brief_id"] == "existing_brief"
    mock_build.assert_not_called()  # Proves caching worked
```

## 5. Required Production Refactoring for Clean Testing

To make these tests entirely robust, the following production refactoring (Dependency Injection) should happen:

1. **LLM Factory Injection**: Currently `ChatGoogleGenerativeAI` is instantiated hardcoded *inside* functions (e.g., `llm = ChatGoogleGenerativeAI(...)` inside `run_agent1`). 
    **Solution:** Pass `llm` as an optional kwarg to `run_agent1(..., llm=None)`. If `None`, instantiate the default. This allows test files to pass in a `FakeLLM` without complex `unittest.mock.patch` spaghetti.

2. **Repository Factory Injection**: Instead of `import` and `await VoiceProfilesRepo.some_method()`, pass a `DataStore` object or use a dependency container, heavily recommended by FastAPI's `Depends()`.

3. **Isolate PydanticOutputParser Chains**: In Agent1 V2, `chain = prompt | llm | parser` is executed internally. Extract this into a helper `_invoke_refinement_chain(llm, prompt_args)` so unit tests can directly mock the parser step instead of trying to mock raw string JSON returns from the LLM.
