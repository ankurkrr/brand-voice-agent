# tests/unit/test_rule_extractor.py

import pytest
from core.voice.rule_extractor import extract_rules_from_text, RuleSchema

@pytest.mark.asyncio
async def test_extract_rules_basic():
    text = """
    DO: Use friendly but confident tone.
    DON'T: Use emojis.
    Preferred vocabulary: "insight", "clarity".
    Forbidden phrases: "unlock your potential".
    Tone: Primary = Professional, Secondary = Friendly
    """

    rules = await extract_rules_from_text(text)

    assert isinstance(rules, dict)
    assert "dos" in rules
    assert "donts" in rules
    assert "tone" in rules
    assert isinstance(rules["dos"], list)
    assert isinstance(rules["tone"], dict)
