"""
Unit Tests for Semantic Preservation Guard

Validates end-to-end semantic preservation during style-only rewrites.
"""

import pytest
from core.voice.semantic_preservation import SemanticPreservationGuard


@pytest.mark.asyncio
async def test_rewrite_preserves_meaning_end_to_end():
    """
    CRITICAL TEST: Verify rewrite changes style but preserves meaning.
    
    This validates CRITICAL FIX #4: cosine similarity ≥ 0.95 enforcement.
    """
    guard = SemanticPreservationGuard()
    
    # Original: Corporate jargon
    original = (
        "We must leverage our synergies to facilitate impactful outcomes "
        "by utilizing best practices and implementing cutting-edge solutions."
    )
    
    # Target: Simplified style (SAME meaning)
    rewrite = (
        "We should use our combined strengths to help create meaningful results "
        "by following proven approaches and adopting innovative solutions."
    )
    
    # Validate semantic preservation
    is_valid, similarity = await guard.validate_rewrite(original, rewrite)
    
    assert is_valid, f"Rewrite should preserve meaning (similarity: {similarity:.3f})"
    assert similarity >= 0.95, f"Similarity {similarity:.3f} below threshold 0.95"
    assert similarity < 1.0, "Not exact match (style should change)"


@pytest.mark.asyncio
async def test_meaning_change_blocked():
    """
    Verify meaning-altering rewrites are BLOCKED.
    """
    guard = SemanticPreservationGuard()
    
    original = "We need to increase revenue by 20% this quarter."
    rewrite = "We should reduce costs to improve profitability."  # DIFFERENT meaning
    
    is_valid, similarity = await guard.validate_rewrite(original, rewrite)
    
    assert not is_valid, "Meaning-altering rewrite should be blocked"
    assert similarity < 0.95, f"Similarity {similarity:.3f} should be below 0.95"


@pytest.mark.asyncio
async def test_style_only_rewrite_workflow():
    """
    End-to-end workflow: rewrite changes tone, preserves facts.
    """
    guard = SemanticPreservationGuard()
    
    # Original: Informal
    original = "Hey! Our new AI tool is super cool and makes writing way easier."
    
    # Rewrite: Formal (SAME facts)
    rewrite = "Our new AI tool significantly enhances writing efficiency."
    
    is_valid, similarity = await guard.validate_rewrite(original, rewrite)
    
    # Should pass (same core message: AI tool improves writing)
    assert is_valid, f"Style-only rewrite should pass (similarity: {similarity:.3f})"
    assert similarity >= 0.75, "Should have reasonable semantic overlap"


@pytest.mark.asyncio
async def test_llm_style_rewrite_with_guard():
    """
    Test the full rewrite_preserving_semantics() flow with LLM.
    
    This simulates the actual production workflow:
    1. Original text (off-brand)
    2. LLM generates style-only rewrite
    3. Guard validates cosine similarity ≥ 0.95
    4. Accept or block
    """
    guard = SemanticPreservationGuard()
    
    original = "Leverage our synergies to achieve impactful outcomes."
    target_style = "casual and friendly (avoid jargon)"
    
    # Perform LLM rewrite with guard
    result = await guard.rewrite_preserving_semantics(
        text=original,
        style_instruction=target_style
    )
    
    assert result["success"], "Rewrite should succeed"
    assert result["similarity"] >= 0.95, f"Similarity {result['similarity']:.3f} below 0.95"
    assert result["rewritten_text"] != original, "Text should change"
    
    # Verify no jargon in rewrite
    rewrite_lower = result["rewritten_text"].lower()
    assert "leverage" not in rewrite_lower, "Should remove 'leverage'"
    assert "synergies" not in rewrite_lower, "Should remove 'synergies'"
