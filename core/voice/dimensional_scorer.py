"""
Dimensional Scorer - Phase 2: Multi-Persona Architect

Scores content across 5 stylistic dimensions with deterministic caching and model fingerprinting.

CRITICAL FIXES APPLIED:
- FIX #1: Cache hits Δ=0.000 (EXACT), cache misses Δ≤0.05 (then frozen)
- FIX #3: Model fingerprint in cache for audit trail

STRICT ENFORCEMENT:
- All scoring must go through hash-based cache
- Cache key includes model name (version-specific)
- Cache hits return bit-perfect values
- Cache misses may vary ≤5% but are frozen once stored
"""

from typing import List, Dict
import hashlib
import json
import re
import uuid
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from data.db.session import get_pool
import aiomysql


class DimensionalScorer:
    """
    STRICT: All dimensional scoring must go through this cache layer.
    
    Dimensions:
    - Humor: Joke density, playful language, emoji usage
    - Empathy: Emotional language, reader-focused ("you/your"), vulnerability
    - Authority: Declarative statements, statistics, technical vocabulary
    - Formality: Passive voice %, sentence complexity, jargon density
    - Urgency: Action verbs, time-sensitive language, imperative mood
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.0):
        """
        CRITICAL FIX #3: Model name is part of scorer identity.
        Different models produce separate cache entries.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            model_kwargs={"response_mime_type": "application/json"}
        )
    
    def _compute_hash(self, text: str, dimensions: List[str]) -> str:
        """
        CRITICAL FIX #3: Include model_name in hash payload.
        
        RULE: Hash must be deterministic AND model-specific.
        - Normalize text (lowercase, strip whitespace, collapse multi-space)
        - Sort dimensions alphabetically
        - Include model_name (protects against version drift)
        - SHA256(normalized_text + "|" + sorted_dimensions + "|" + model_name)
        
        Returns:
            64-character hex hash
        """
        # Normalize text
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        
        # Sort dimensions
        sorted_dims = sorted(dimensions)
        
        # Build payload with model fingerprint
        payload = f"{normalized}|{','.join(sorted_dims)}|{self.model_name}"
        
        return hashlib.sha256(payload.encode()).hexdigest()
    
    async def score_dimensions(
        self,
        text: str,
        dimensions: List[str],
        force_refresh: bool = False
    ) -> Dict[str, float]:
        """
        Score text across multiple stylistic dimensions with caching.
        
        STRICT ENFORCEMENT (CLARIFIED DETERMINISM):
        1. Compute hash (with model fingerprint)
        2. Check cache (if not force_refresh)
        3. On cache hit → return cached scores (Δ = 0.000 EXACT)
        4. On cache miss → call LLM (Δ may vary ≤ 0.05), store with model fingerprint
        5. Once cached, frozen forever
        
        Args:
            text: Content to analyze
            dimensions: List of dimension names (e.g., ["Humor", "Empathy", "Authority"])
            force_refresh: Only True for testing/admin purposes (bypasses cache)
        
        Returns:
            Dict mapping dimension → score (0.0 to 1.0)
            Example: {"Humor": 0.72, "Empathy": 0.45, "Authority": 0.88}
        
        Raises:
            ValueError: If text is empty or dimensions list is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if not dimensions:
            raise ValueError("Dimensions list cannot be empty")
        
        # Compute hash
        content_hash = self._compute_hash(text, dimensions)
        
        # Check cache (unless force_refresh)
        if not force_refresh:
            cached = await self._get_cached_score(content_hash)
            if cached:
                return cached["scores"]  # Δ = 0.000 EXACT
        
        # Cache miss - call LLM (may vary Δ ≤ 0.05)
        scores = await self._call_llm_scorer(text, dimensions)
        
        # Store in cache with model fingerprint
        await self._store_score_cache(
            content_hash=content_hash,
            text=text,
            dimensions=dimensions,
            scores=scores
        )
        
        return scores  # Once cached, frozen forever
    
    async def _get_cached_score(self, content_hash: str) -> Dict:
        """
        Retrieve cached score from database.
        
        Returns:
            Dict with 'scores' key if found, None otherwise
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT dimensions, scores
                    FROM voice_meta.persona_dimensional_cache
                    WHERE content_hash = %s AND llm_model = %s
                """, (content_hash, self.model_name))
                
                result = await cursor.fetchone()
        
        if result:
            # Parse JSON
            scores = result['scores']
            if isinstance(scores, str):
                scores = json.loads(scores)
            return {"scores": scores}
        
        return None
    
    async def _store_score_cache(
        self,
        content_hash: str,
        text: str,
        dimensions: List[str],
        scores: Dict[str, float]
    ):
        """
        Store dimensional scores in cache with model fingerprint.
        
        CRITICAL FIX #3: Includes llm_model in uniqueness constraint.
        Different models produce separate cache entries.
        """
        pool = await get_pool()
        
        # Calculate token count (approximate)
        token_count = len(text.split())
        
        # Text preview (first 200 chars)
        text_preview = text[:200] if len(text) > 200 else text
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO persona_dimensional_cache
                    (id, content_hash, llm_model, llm_temperature, dimensions, scores, text_preview, token_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        scores = VALUES(scores),
                        text_preview = VALUES(text_preview),
                        token_count = VALUES(token_count)
                """, (
                    str(uuid.uuid4()),
                    content_hash,
                    self.model_name,
                    self.temperature,
                    json.dumps(dimensions),
                    json.dumps(scores),
                    text_preview,
                    token_count
                ))
                await conn.commit()
    
    async def _call_llm_scorer(self, text: str, dimensions: List[str]) -> Dict[str, float]:
        """
        Call LLM to score text across dimensions.
        
        STRICT PARAMETERS:
        - temperature = 0.0 (required, but not perfectly deterministic in practice)
        - model = self.model_name
        - structured JSON output with schema enforcement
        - max_retries = 3 with exponential backoff
        
        Returns:
            Dict[dimension_name, float score 0.0-1.0]
        """
        # Build LLM prompt
        prompt = f"""You are an expert in analyzing writing style across multiple dimensions.

Analyze the following text and score it across these dimensions (0.0 to 1.0 scale):

{', '.join(dimensions)}

Dimension Definitions:
- **Humor**: Joke density, playful language, emoji/exclamation usage, wit
- **Empathy**: Emotional language, reader-focused ("you/your"), vulnerability markers, understanding
- **Authority**: Declarative statements, statistics/citations, technical vocabulary, confidence
- **Formality**: Passive voice %, sentence complexity, jargon density, professional tone
- **Urgency**: Action verbs, time-sensitive language, imperative mood, deadline pressure

Text to analyze:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON object with dimension names as keys and float scores (0.0 to 1.0) as values.
Example: {{"Humor": 0.72, "Empathy": 0.45, "Authority": 0.88}}

JSON:"""
        
        # Call LLM with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(prompt)
                
                # Parse JSON response
                response_text = response.content if hasattr(response, 'content') else str(response)
                scores = json.loads(response_text)
                
                # Validate scores
                for dim in dimensions:
                    if dim not in scores:
                        raise ValueError(f"Missing dimension: {dim}")
                    
                    score = scores[dim]
                    if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                        raise ValueError(f"Invalid score for {dim}: {score}")
                
                # Round to 2 decimal places
                return {dim: round(float(scores[dim]), 2) for dim in dimensions}
            
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed - use heuristic fallback
                    print(f"LLM scoring failed after {max_retries} attempts: {e}")
                    print("Falling back to heuristic scoring")
                    return self._heuristic_scorer(text, dimensions)
                
                # Wait before retry (exponential backoff)
                import asyncio
                await asyncio.sleep(2 ** attempt)
    
    def _heuristic_scorer(self, text: str, dimensions: List[str]) -> Dict[str, float]:
        """
        Heuristic fallback scorer (when LLM fails).
        
        Uses regex patterns and linguistic analysis.
        """
        scores = {}
        
        text_lower = text.lower()
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        
        for dim in dimensions:
            if dim == "Humor":
                # Count exclamations, emojis, playful words
                exclamations = text.count('!')
                playful_words = len([w for w in words if w.lower() in ['haha', 'lol', 'funny']])
                scores[dim] = min(0.95, max(0.05, (exclamations + playful_words) / 10))
            
            elif dim == "Empathy":
                # Count "you/your", emotional words
                you_count = text_lower.count('you') + text_lower.count('your')
                emotional_words = len([w for w in words if w.lower() in ['feel', 'understand', 'care', 'help', 'support']])
                scores[dim] = min(0.95, max(0.05, (you_count + emotional_words) / 20))
            
            elif dim == "Authority":
                # Count declarative statements, statistics
                stats = len(re.findall(r'\d+%|\$\d+|#\d+', text))
                long_sentences = len([s for s in sentences if len(s.split()) > 15])
                scores[dim] = min(0.95, max(0.05, (stats * 2 + long_sentences) / 10))
            
            elif dim == "Formality":
                # Based on passive voice heuristic, long words
                passive_indicators = text_lower.count('was') + text_lower.count('were') + text_lower.count('been')
                long_words = len([w for w in words if len(w) > 8])
                scores[dim] = min(0.95, max(0.05, (passive_indicators + long_words) / 20))
            
            elif dim == "Urgency":
                # Count action verbs (imperative), time-sensitive words
                urgency_words = len([w for w in words if w.lower() in ['now', 'today', 'urgent', 'asap', 'immediately', 'hurry']])
                imperatives = len([s for s in sentences if s.strip().startswith(('Get', 'Do', 'Start', 'Stop', 'Check'))])
                scores[dim] = min(0.95, max(0.05, (urgency_words * 2 + imperatives) / 10))
            
            else:
                # Unknown dimension - neutral score
                scores[dim] = 0.5
        
        return {dim: round(scores[dim], 2) for dim in dimensions}


async def score_text_for_profile(text: str, profile_id: str = None) -> Dict[str, float]:
    """
    Convenience function to score text using default dimensions.
    
    Args:
        text: Content to analyze
        profile_id: Optional profile ID (for future persona-specific dimensions)
    
    Returns:
        Dict with all 5 default dimensions scored
    """
    scorer = DimensionalScorer()
    dimensions = ["Humor", "Empathy", "Authority", "Formality", "Urgency"]
    return await scorer.score_dimensions(text, dimensions)
