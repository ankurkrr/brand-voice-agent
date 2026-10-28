"""
Unit Tests for Persona Resolver - Phase 2

Tests circular chain detection, inheritance merging, and conflict detection.
"""

import pytest
import asyncio
from core.voice.persona_resolver import (
    resolve_effective_persona,
    PersonaNotFoundError,
    PersonaConflictError,
    _detect_rule_conflicts
)


@pytest.mark.asyncio
async def test_resolve_root_persona():
    """Test resolving a root persona (no parent)."""
    # This requires a real database with migrated V1 profile
    # Replace 'test_persona_id' with actual persona_id from your database
    
    # persona = await resolve_effective_persona("test_persona_id")
    
    # assert persona.persona_id is not None
    # assert persona.hierarchy_depth == 0
    # assert persona.parent_persona_id is None
    # assert len(persona.dimensional_scores) == 5
    
    # Placeholder - implement after migration
    pytest.skip("Requires migrated V1 database")


@pytest.mark.asyncio
async def test_circular_chain_detection():
    """
    CRITICAL FIX #2: Test that circular chains are detected.
    
    Note: This requires manually creating circular reference in database:
    INSERT INTO voice_profiles ... SET parent_persona_id to create A→B→C→A
    """
    # pytest.skip("Requires manual circular reference setup")
    
    # Example test structure:
    # with pytest.raises(PersonaConflictError, match="Circular persona inheritance"):
    #     await resolve_effective_persona("persona_a")
    
    pytest.skip("Requires manual database setup with circular reference")


def test_rule_conflicts_detection():
    """Test conflict detection between DOs and DON'Ts."""
    # Test case 1: Jargon conflict
    dos = ["Use technical terms when explaining features"]
    donts = ["Avoid jargon and specialized vocabulary"]
    
    conflicts = _detect_rule_conflicts(dos, donts)
    
    # Should detect conflict (specialized vocabulary vs jargon)
    assert len(conflicts) > 0, "Should detect jargon/technical conflict"
    assert any("jargon" in c.lower() for c in conflicts)


def test_no_false_conflicts():
    """Test that non-conflicting rules don't raise false positives."""
    dos = ["Be friendly and approachable"]
    donts = ["Use overly formal language"]
    
    conflicts = _detect_rule_conflicts(dos, donts)
    
    # Should NOT detect conflict (friendly vs formal is valid differentiation)
    assert len(conflicts) == 0, "Should not detect conflict for valid differentiation"


@pytest.mark.asyncio
async def test_persona_not_found():
    """Test that invalid persona_id raises PersonaNotFoundError."""
    with pytest.raises(PersonaNotFoundError, match="not found"):
        await resolve_effective_persona("invalid_persona_id_12345")


def test_inheritance_union_logic():
    """
    Test that forbidden phrases are UNION (not overridden).
    This is a manual verification test - inspect resolved persona.
    """
    # Manual test: Create parent with forbidden=["leverage"]
    # Create child with forbidden=["synergy"]
    # Resolve child - should have both ["leverage", "synergy"]
    
    pytest.skip("Manual verification test - requires database setup")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
