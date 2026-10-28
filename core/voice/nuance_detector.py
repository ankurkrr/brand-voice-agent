"""
Nuance Detector - Phase 2: Multi-Persona Architect

Real-time detection of off-brand phrases with length-aware thresholds.

CRITICAL FIX #3 APPLIED:
- Length-aware vocabulary thresholds (35% <50 tokens, 60% >200 tokens)
- Vocabulary divergence alone cannot hard-fail (only medium severity)
- Must provide suggested rewrite to flag

STRICT ENFORCEMENT:
- Forbidden phrases always severity="high"
- Dimensional drift only severity="medium"
- Vocabulary divergence only severity="medium" (AND only if suggestion exists)
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import re
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import numpy as np


class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NuanceViolation:
    """Represents a single off-brand phrase/pattern detection."""
    phrase: str
    reason: str
    severity: ViolationSeverity
    suggestion: Optional[str] = None
    token_count: Optional[int] = None
    threshold_applied: Optional[float] = None
    actual_overlap: Optional[float] = None


class NuanceDetector:
    """
    STRICT: Real-time off-brand phrase detection with length-aware thresholds.
    
    Detection strategies:
    1. Forbidden phrase semantic matching (using Google Embeddings)
    2. Dimensional drift detection
    3. Length-aware vocabulary divergence
    4. LLM-powered nuance analysis (optional)
    """
    
    def __init__(self):
        """Initialize with Google Gemini embeddings for semantic similarity."""
        self.embedder = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    @staticmethod
    def calculate_vocab_threshold(token_count: int) -> float:
        """
        CRITICAL FIX #3: Dynamic threshold based on content length.
        
        RULE: Threshold decreases for shorter content, increases for longer.
        
        Rationale:
        - Short text (<50 tokens): Very specific, allow more brand vocab deviation → 35%
        - Medium text (50-200): Standard content → 50%
        - Long text (200+): Should have strong brand signal → 60%
        
        Formula: Piecewise linear interpolation
        
        Args:
            token_count: Number of tokens in generated text
        
        Returns:
            Threshold (0.35 to 0.60)
        """
        if token_count < 50:
            return 0.35
        elif token_count < 200:
            # Linear interpolation: 35% at 50 tokens → 60% at 200 tokens
            return 0.35 + (0.25 * (token_count - 50) / 150)
        else:
            return 0.60
    
    async def detect_nuances(
        self,
        generated_text: str,
        voice_profile: Dict
    ) -> List[NuanceViolation]:
        """
        Identify off-brand language patterns in generated text.
        
        Args:
            generated_text: Content to validate
            voice_profile: Resolved persona's voice profile
        
        Returns:
            List of violations (empty if compliant)
        """
        violations = []
        
        # Strategy 1: Forbidden phrase matching (exact + fuzzy)
        forbidden_violations = self._detect_forbidden_phrases(
            generated_text,
            voice_profile.get("explicit_rules", {}).get("forbidden_phrases", [])
        )
        violations.extend(forbidden_violations)
        
        # Strategy 2: Dimensional drift detection
        if "dimensional_scores" in voice_profile:
            drift_violations = await self._detect_dimensional_drift(
                generated_text,
                voice_profile["dimensional_scores"]
            )
            violations.extend(drift_violations)
        
        # Strategy 3: Length-aware vocabulary divergence
        preferred_vocab = voice_profile.get("explicit_rules", {}).get("preferred_vocabulary", [])
        if preferred_vocab:
            vocab_violation = self._detect_vocabulary_divergence(
                generated_text,
                preferred_vocab
            )
            if vocab_violation:
                violations.append(vocab_violation)
        
        return violations
    
    def _detect_forbidden_phrases(
        self,
        text: str,
        forbidden_phrases: List[str]
    ) -> List[NuanceViolation]:
        """
        Detect forbidden phrases using DUAL strategy:
        1. RapidFuzz for typo/spelling tolerance (string-level)
        2. Google Embeddings for semantic similarity (meaning-level)
        
        STRICT: All forbidden phrases have severity="high"
        
        This approach detects:
        - Exact matches (fast path)
        - Typos/spelling variants via RapidFuzz (e.g., "levrage" → "leverage")
        - Semantic equivalents via embeddings (e.g., "utilize" ≈ "leverage")
        """
        violations = []
        
        if not forbidden_phrases:
            return violations
        
        text_lower = text.lower()
        
        # FAST PATH: Exact word match
        for phrase in forbidden_phrases:
            if phrase.lower() in text_lower:
                violations.append(NuanceViolation(
                    phrase=phrase,
                    reason=f"Forbidden phrase (exact match)",
                    severity=ViolationSeverity.HIGH,
                    suggestion=self._suggest_replacement(phrase)
                ))
        
        # TYPO DETECTION: RapidFuzz for spelling variants
        # This catches "levrage", "leverege", etc. → "leverage"
        from rapidfuzz import fuzz
        
        words = text_lower.split()
        for word in words:
            if len(word) < 4:  # Skip short words
                continue
            
            for phrase in forbidden_phrases:
                phrase_lower = phrase.lower()
                similarity = fuzz.ratio(word, phrase_lower)
                
                # 85% similarity = likely typo/variant
                if similarity > 85:
                    # Check if not already caught
                    if not any(v.phrase == word for v in violations):
                        violations.append(NuanceViolation(
                            phrase=word,
                            reason=f"Typo/variant of forbidden phrase '{phrase}' ({similarity}% similar)",
                            severity=ViolationSeverity.HIGH,
                            suggestion=self._suggest_replacement(phrase)
                        ))
                        break
        
        # SEMANTIC DETECTION: Embeddings for meaning-based matches
        # This catches "utilize", "make use of", etc. ≈ "leverage"
        
        # Batch embed forbidden phrases
        # Result is List[List[float]] -> convert to List[np.array]
        try:
            raw_embeddings = self.embedder.embed_documents(forbidden_phrases)
            forbidden_embeddings = [np.array(emb) for emb in raw_embeddings]
        except Exception as e:
            print(f"Embedding error: {e}")
            return violations

        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue
            
            try:
                # Embed single sentence
                sent_emb_list = self.embedder.embed_query(sentence)
                sentence_embedding = np.array(sent_emb_list)
            except Exception:
                continue
            
            for i, forbidden_phrase in enumerate(forbidden_phrases):
                similarity = self._cosine_similarity(
                    sentence_embedding,
                    forbidden_embeddings[i]
                )
                
                # Threshold: 0.85 = semantically similar (higher threshold for Gemini embeddings)
                if similarity > 0.85:
                    # Check if not already caught by exact/typo detection
                    if not any(forbidden_phrase.lower() in v.phrase.lower() for v in violations):
                        violations.append(NuanceViolation(
                            phrase=sentence[:100],  # First 100 chars
                            reason=f"Semantically similar to forbidden phrase '{forbidden_phrase}' (similarity: {similarity:.2f})",
                            severity=ViolationSeverity.HIGH,
                            suggestion=self._suggest_replacement(forbidden_phrase)
                        ))
                        break
        
        return violations
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2)
        )
    
    async def _detect_dimensional_drift(
        self,
        generated_text: str,
        expected_scores: Dict[str, float],
        threshold: float = 0.3
    ) -> List[NuanceViolation]:
        """
        Detect dimensional drift (generated content differs from profile).
        
        STRICT: Dimensional drift always severity="medium" (never "high")
        
        Args:
            generated_text: Content to check
            expected_scores: Target dimensional scores from profile
            threshold: Maximum allowed deviation (default 0.3)
        
        Returns:
            List of violations (severity="medium")
        """
        from core.voice.dimensional_scorer import DimensionalScorer
        
        if not expected_scores:
            return []
            
        scorer = DimensionalScorer()
        dimensions = list(expected_scores.keys())
        
        # Score generated text
        actual_scores = await scorer.score_dimensions(generated_text, dimensions)
        
        violations = []
        for dim, expected in expected_scores.items():
            actual = actual_scores.get(dim, 0.5)
            drift = abs(actual - expected)
            
            if drift > threshold:
                # STRICT: Only medium severity
                violations.append(NuanceViolation(
                    phrase=f"[dimensional drift: {dim}]",
                    reason=f"{dim} drift detected (expected {expected:.2f}, got {actual:.2f}, drift {drift:.2f})",
                    severity=ViolationSeverity.MEDIUM,
                    suggestion=f"Adjust {dim} to ~{expected:.2f} (currently {actual:.2f})"
                ))
        
        return violations
    
    def _detect_vocabulary_divergence(
        self,
        generated_text: str,
        preferred_vocab: List[str]
    ) -> Optional[NuanceViolation]:
        """
        Detect vocabulary divergence with length-aware thresholds.
        
        STRICT ENFORCEMENT:
        1. Count tokens in generated text
        2. Calculate dynamic threshold
        3. Compute overlap %
        4. If below threshold AND suggestion exists → flag as MEDIUM
        5. If below threshold but NO suggestion → do NOT flag
        
        STRICT RULES:
        - Vocabulary divergence NEVER has severity="high" (only "medium")
        - Can only flag if suggestion exists
        - Threshold varies by content length
        
        Returns:
            NuanceViolation with severity="medium" or None
        """
        tokens = self._tokenize(generated_text)
        token_count = len(tokens)
        threshold = self.calculate_vocab_threshold(token_count)
        
        overlap = self._compute_overlap(tokens, preferred_vocab)
        
        if overlap < threshold:
            suggestion = self._suggest_vocab_improvement(tokens, preferred_vocab)
            
            # STRICT: Only flag if suggestion exists
            if suggestion:
                return NuanceViolation(
                    phrase="[vocabulary divergence]",
                    reason=f"Only {overlap:.0%} overlap with brand vocab (expected ≥{threshold:.0%} for {token_count} tokens)",
                    severity=ViolationSeverity.MEDIUM,
                    suggestion=suggestion,
                    token_count=token_count,
                    threshold_applied=threshold,
                    actual_overlap=overlap
                )
        
        return None
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words (simple whitespace split)."""
        # Remove punctuation and split
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        return [w for w in text_clean.split() if len(w) > 2]  # Ignore short words
    
    def _compute_overlap(self, tokens: List[str], preferred_vocab: List[str]) -> float:
        """
        Compute overlap percentage between tokens and preferred vocabulary.
        
        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        if not tokens:
            return 0.0
        
        preferred_set = set(word.lower() for word in preferred_vocab)
        token_set = set(tokens)
        
        overlap_count = len(token_set.intersection(preferred_set))
        return overlap_count / len(token_set) if token_set else 0.0
    
    def _suggest_vocab_improvement(
        self,
        tokens: List[str],
        preferred_vocab: List[str]
    ) -> Optional[str]:
        """
        Suggest vocabulary improvements.
        
        Returns:
            Suggestion string or None if no improvement possible
        """
        preferred_set = set(word.lower() for word in preferred_vocab)
        missing_words = [t for t in tokens if t not in preferred_set]
        
        if not missing_words:
            return None
        
        # Find preferred alternatives for missing words
        # (In production, use embeddings for semantic similarity)
        alternatives = []
        for word in missing_words[:3]:  # Suggest up to 3 replacements
            # Simple keyword mapping (expand in production)
            if alt := self._get_alternative(word, preferred_set):
                alternatives.append(f"'{word}' → '{alt}'")
        
        if alternatives:
            return f"Consider using: {', '.join(alternatives)}"
        
        return None
    
    def _get_alternative(self, word: str, preferred_vocab: set) -> Optional[str]:
        """Find preferred alternative for a word."""
        # Simple keyword mapping (production should use embeddings)
        alternatives_map = {
            'leverage': 'use',
            'utilize': 'use',
            'synergy': 'collaboration',
            'impactful': 'meaningful',
            'outcomes': 'results',
            'facilitate': 'help',
            'implement': 'do',
        }
        
        if word in alternatives_map:
            suggested = alternatives_map[word]
            if suggested in preferred_vocab:
                return suggested
        
        return None
    
    def _suggest_replacement(self, forbidden_phrase: str) -> Optional[str]:
        """Suggest replacement for forbidden phrase."""
        # Simple replacement mapping (expand in production)
        replacements = {
            'leverage': 'use',
            'synergy': 'teamwork',
            'synergies': 'combined strengths',
            'utilize': 'use',
            'impactful': 'meaningful',
            'outcomes': 'results',
            'best practice': 'proven approach',
            'cutting-edge': 'innovative',
            'game-changer': 'significant advancement',
        }
        
        return replacements.get(forbidden_phrase.lower())


async def validate_voice_compliance(
    generated_text: str,
    voice_profile: Dict
) -> Dict:
    """
    Validate generated text against voice profile.
    
    Args:
        generated_text: Content to validate
        voice_profile: Resolved persona's voice profile
    
    Returns:
        Dict with:
        - is_compliant: bool
        - violations: List[NuanceViolation]
        - suggested_rewrites: List[str]
    """
    detector = NuanceDetector()
    violations = await detector.detect_nuances(generated_text, voice_profile)
    
    # Filter to medium/high severity only
    significant_violations = [v for v in violations if v.severity in [ViolationSeverity.MEDIUM, ViolationSeverity.HIGH]]
    
    return {
        "is_compliant": len(significant_violations) == 0,
        "violations": significant_violations,
        "suggested_rewrites": [v.suggestion for v in significant_violations if v.suggestion]
    }
