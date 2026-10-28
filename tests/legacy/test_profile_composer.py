# tests/unit/test_profile_composer.py

import pytest
from unittest.mock import patch
from core.voice.profile_composer import compose_voice_profile
from langchain_core.documents import Document

@pytest.mark.asyncio
async def test_compose_voice_profile_structure():

    docs = [Document(page_content="This is a test document. It has style!")]

    fake_rules = {
        "dos": ["Be clear"],
        "donts": ["Avoid jargon"],
        "forbidden_phrases": ["unlock potential"],
        "preferred_vocabulary": ["clarity"],
        "tone": {"primary": "Professional", "secondary": ["Friendly"]},
    }

    fake_examples = [
        {"text": "Example snippet 1"},
        {"text": "Example snippet 2"},
        {"text": "Example snippet 3"},
    ]

    # Patch all external dependencies
    with patch("core.voice.profile_composer.extract_rules_from_text", return_value=fake_rules), \
         patch("core.voice.profile_composer.select_best_examples", return_value=fake_examples), \
         patch("services.db.voice_profiles_repo.VoiceProfilesRepo.save_profile") as mock_save:

        mock_save.return_value = {
            "profile_id": "test123",
            "brand_id": "brand_001",
            "profile_data": {}
        }

        result = await compose_voice_profile(
            brand_id="brand_001",
            source_docs=docs,
            source_text_for_rules="test rules",
            collection_name="brand_brand_001"
        )

    assert result["profile_id"] == "test123"
    assert mock_save.called
