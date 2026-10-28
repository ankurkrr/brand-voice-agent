import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Pre-fill Database ENVs to prevent session.py from crashing on import
os.environ["DB_HOST"] = "mock_host"
os.environ["DB_USER"] = "mock_user"
os.environ["DB_PASSWORD"] = "mock_pass"
os.environ["DB_NAME"] = "mock_db"

# Mock heavy/missing ML dependencies for pure unit testing without full environment
import sys
for mod in ['aiomysql']:
    sys.modules[mod] = MagicMock()

# Setup Fake Async Context Manager for Database calls
mock_cursor = MagicMock()
mock_cursor.__aenter__ = AsyncMock()
mock_cursor.__aexit__ = AsyncMock(return_value=None)

mock_conn = MagicMock()
mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
mock_conn.__aexit__ = AsyncMock(return_value=None)
mock_conn.cursor.return_value = mock_cursor

mock_pool = MagicMock()
mock_pool.acquire.return_value = mock_conn
sys.modules['aiomysql'].create_pool = AsyncMock(return_value=mock_pool)

import pytest

# --- Repositories Mock ---
@pytest.fixture
def mock_voice_profiles_repo(mocker):
    repo = mocker.patch("data.repos.voice_profiles.VoiceProfilesRepo")
    repo.get_active_profile = AsyncMock()
    repo.save_profile = AsyncMock()
    repo.update_human_profile = AsyncMock()
    repo.get_profile_by_brand_id = AsyncMock()
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

@pytest.fixture
def mock_brands_repo(mocker):
    repo = mocker.patch("data.repos.brands.BrandsRepo")
    repo.get_brand_by_id = AsyncMock()
    repo.create_brand = AsyncMock()
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
            import json
            try:
                return json.loads(self.content)
            except:
                return {"error": "Invalid JSON mock"}

    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke.return_value = MockResponse(
        content='{"dos": ["Be kind"], "donts": ["Be rude"], "tone": {"primary": "Professional"}, "forbidden_phrases": [], "preferred_vocabulary": []}'
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
