"""
Unit Tests for Nuance Detector - Phase 2

Tests length-aware thresholds, forbidden phrase detection, and severity rules.
"""

import pytest
import asyncio
from core.voice.nuance_detector import (
    NuanceDetector,
    ViolationSeverity,
    validate_voice_compliance
)


def test_length_aware_threshold_short():
    """CRITICAL FIX #3: Short text (<50 tokens) should use 35% threshold."""
    detector = NuanceDetector()
    
    threshold = detector.calculate_vocab_threshold(30)
    assert threshold == 0.35, f"Short text threshold should be 0.35, got {threshold}"


def test_length_aware_threshold_medium():
    """CRITICAL FIX #3: Medium text (50-200 tokens) should interpolate."""
    detector = NuanceDetector()
    
    # At 50 tokens, should be 0.35
    threshold_50 = detector.calculate_vocab_threshold(50)
    assert threshold_50 == 0.35
    
    # At 125 tokens (midpoint), should be around 0.475
    threshold_125 = detector.calculate_vocab_threshold(125)
    assert 0.45 <= threshold_125 <= 0.50, f"Medium threshold should be ~0.475, got {threshold_125}"
    
    # At 200 tokens, should be 0.60
    threshold_200 = detector.calculate_vocab_threshold(200)
    assert threshold_200 == 0.60


def test_length_aware_threshold_long():
    """CRITICAL FIX #3: Long text (>200 tokens) should use 60% threshold."""
    detector = NuanceDetector()
    
    threshold = detector.calculate_vocab_threshold(500)
    assert threshold == 0.60, f"Long text threshold should be 0.60, got {threshold}"


@pytest.mark.asyncio
async def test_forbidden_phrase_exact_match():
    """Test forbidden phrase detection with exact match."""
    detector = NuanceDetector()
    
    text = "Let's leverage our synergies to maximize outcomes!"
    forbidden = ["leverage", "synergy", "maximize"]
    
    violations = detector._detect_forbidden_phrases(text, forbidden)
    
    # Should detect "leverage" and "synergies" (plural of "synergy")
    assert len(violations) >= 1, "Should detect forbidden phrases"
    
    # All forbidden phrase violations should be HIGH severity
    for v in violations:
        assert v.severity == ViolationSeverity.HIGH, f"Forbidden phrases must be HIGH severity, got {v.severity}"


@pytest.mark.asyncio
async def test_forbidden_phrase_fuzzy_match():
    """Test fuzzy matching for typos/variants."""
    detector = NuanceDetector()
    
    text = "Let's levrage our resources"  # Typo: "levrage" instead of "leverage"
    forbidden = ["leverage"]
    
    violations = detector._detect_forbidden_phrases(text, forbidden)
    
    # Should detect fuzzy match (85%+ similar)
    assert len(violations) > 0, "Should detect fuzzy match for typos"
    assert violations[0].severity == ViolationSeverity.HIGH


@pytest.mark.asyncio
async def test_vocab_divergence_severity():
    """
    STRICT RULE: Vocabulary divergence must NEVER be severity="high".
    Only "medium" and only if suggestion exists.
    """
    detector = NuanceDetector()
    
    preferred_vocab = ["team", "collaborate", "achieve", "result"]
    text = "We utilize synergistic methodologies to maximize outcomes."  # No preferred words
    
    violation = detector._detect_vocabulary_divergence(text, preferred_vocab)
    
    if violation:
        # STRICT: Must be MEDIUM (never HIGH)
        assert violation.severity == ViolationSeverity.MEDIUM, \
            f"Vocabulary divergence must be MEDIUM severity, got {violation.severity}"
        
        # STRICT: Must have suggestion (only flags if suggestion exists)
        assert violation.suggestion is not None, \
            "Vocabulary divergence should only flag if suggestion exists"


@pytest.mark.asyncio
async def test_no_violation_without_suggestion():
    """
    STRICT RULE: Vocabulary divergence should NOT flag if no suggestion available.
    """
    detector = NuanceDetector()
    
    # Use technical terms that don't have clear alternatives
    preferred_vocab = ["team"]
    text = "Implementing asynchronous microservices architecture."  # Technical, no alternatives
    
    violation = detector._detect_vocabulary_divergence(text, preferred_vocab)
    
    # Should NOT flag (no meaningful suggestion possible)
    # Or if flagged, must have a suggestion
    if violation:
        assert violation.suggestion is not None


@pytest.mark.asyncio
async def test_dimensional_drift_severity():
    """
    STRICT RULE: Dimensional drift must be severity="medium" (never "high").
    """
    detector = NuanceDetector()
    
    generated_text = "This is a very formal, authoritative statement with high complexity."
    expected_scores = {
        "Formality": 0.3,  # Expected low formality
        "Authority": 0.2    # Expected low authority
    }
    
    violations = await detector._detect_dimensional_drift(generated_text, expected_scores, threshold=0.3)
    
    if violations:
        for v in violations:
            # STRICT: Must be MEDIUM (never HIGH)
            assert v.severity == ViolationSeverity.MEDIUM, \
                f"Dimensional drift must be MEDIUM severity, got {v.severity}"


def test_tokenization_normalizes():
    """Test that tokenization normalizes punctuation."""
    detector = NuanceDetector()
    
    text = "Hello! This is a test... with punctuation??"
    tokens = detector._tokenize(text)
    
    # Should remove punctuation
    assert "hello" in tokens
    assert "test" in tokens
    assert "!" not in tokens
    assert "?" not in tokens


def test_overlap_computation():
    """Test vocabulary overlap calculation."""
    detector = NuanceDetector()
    
    tokens = ["team", "work", "together", "achieve", "goal"]
    preferred = ["team", "collaborate", "achieve", "result"]
    
    overlap = detector._compute_overlap(tokens, preferred)
    
    # "team" and "achieve" overlap = 2 out of 5 tokens = 40%
    assert overlap == 0.4, f"Expected 40% overlap, got {overlap * 100}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
