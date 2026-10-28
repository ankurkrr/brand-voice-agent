"""
Semantic Preservation Rewrite Guard - Phase 2: Multi-Persona Architect

Ensures rewrites preserve meaning while fixing voice compliance violations.

CRITICAL FIX #4 APPLIED:
- Cosine similarity ≥ 0.95 required for all rewrites
- Rewrites may change STYLE only, never MEANING
- Protects against liability in enterprise/legal contexts

STRICT ENFORCEMENT:
- Rewrite rejected if similarity < 0.95
- Max 2 rewrite attempts
- LLM prompt explicitly instructs style-only changes
"""

from typing import List, Dict
import numpy as np
import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from core.voice.nuance_detector import NuanceViolation


class RewriteViolationError(ValueError):
    """Raised when rewrite alters semantic meaning beyond allowed threshold."""
    pass


class SemanticPreservationGuard:
    """
    CRITICAL FIX #4: Enforce semantic preservation during rewrites.
    
    Rewrites may change style only, never meaning.
    """
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Args:
            similarity_threshold: Minimum cosine similarity (default 0.95)
        """
        self.similarity_threshold = similarity_threshold
        self.embedder = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3  # Some creativity for rewrites
        )
    
    async def rewrite_with_semantic_preservation(
        self,
        original_content: str,
        violations: List[NuanceViolation],
        voice_profile: Dict,
        max_attempts: int = 2
    ) -> str:
        """
        Rewrite content to fix violations while preserving semantic meaning.
        
        STRICT ENFORCEMENT:
        - Cosine similarity between original and rewritten must be ≥ 0.95
        - If similarity < 0.95, rewrite is REJECTED (altered meaning too much)
        - This protects against liability in legal/enterprise contexts
        
        Args:
            original_content: Original generated content
            violations: List of nuance violations to fix
            voice_profile: Brand voice profile
            max_attempts: Maximum rewrite attempts (default 2)
        
        Returns:
            Rewritten content that passes compliance AND semantic preservation
        
        Raises:
            RewriteViolationError: If semantic similarity < 0.95 threshold
        """
        original_embedding = self.embedder.embed_query(original_content)
        
        for attempt in range(max_attempts):
            # Generate rewrite using LLM
            rewritten = await self._generate_rewrite(
                original_content,
                violations,
                voice_profile,
                attempt_number=attempt + 1
            )
            
            # CRITICAL: Check semantic preservation
            rewritten_embedding = self.embedder.embed_query(rewritten)
            similarity = self._cosine_similarity(original_embedding, rewritten_embedding)
            
            if similarity < self.similarity_threshold:
                raise RewriteViolationError(
                    f"Rewrite attempt {attempt + 1} altered semantic meaning beyond allowed threshold.\n"
                    f"Semantic similarity: {similarity:.3f} (required ≥ {self.similarity_threshold})\n"
                    f"Original: {original_content[:100]}...\n"
                    f"Rewritten: {rewritten[:100]}...\n"
                    f"RULE: Rewrites may change style only, never meaning."
                )
            
            # Check if rewrite passes compliance
            from core.voice.nuance_detector import NuanceDetector
            detector = NuanceDetector()
            new_violations = await detector.detect_nuances(rewritten, voice_profile)
            
            # Filter to high severity only (medium is acceptable)
            high_severity_violations = [
                v for v in new_violations
                if v.severity == "high"
            ]
            
            if not high_severity_violations:
                # Success: compliant AND semantically preserved
                return rewritten
        
        # Failed after max_attempts
        raise RewriteViolationError(
            f"Could not fix violations in {max_attempts} attempts while preserving meaning.\n"
            f"Original violations: {[v.phrase for v in violations]}"
        )
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two embedding vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    async def _generate_rewrite(
        self,
        original: str,
        violations: List[NuanceViolation],
        voice_profile: Dict,
        attempt_number: int
    ) -> str:
        """
        Generate rewrite using LLM with explicit style-only instructions.
        """
        # Build violation descriptions
        violation_desc = "\n".join([
            f"- \"{v.phrase}\": {v.reason} (Suggestion: {v.suggestion or 'N/A'})"
            for v in violations
        ])
        
        # Get brand guidelines
        tone = voice_profile.get("explicit_rules", {}).get("tone", {})
        dos = voice_profile.get("explicit_rules", {}).get("dos", [])
        donts = voice_profile.get("explicit_rules", {}).get("donts", [])
        
        prompt = f"""You are a brand voice compliance editor. Your task is to rewrite content to fix voice violations while PRESERVING THE EXACT MEANING.

**CRITICAL RULE**: You may ONLY change the STYLE and WORDING. You MUST NOT change the MEANING or FACTS.

Original content:
\"\"\"
{original}
\"\"\"

Voice violations to fix (attempt {attempt_number}/{attempt_number}):
{violation_desc}

Brand voice guidelines:
- Tone: {tone.get('primary', 'neutral')}
- DO: {', '.join(dos[:3]) if dos else 'N/A'}
- DON'T: {', '.join(donts[:3]) if donts else 'N/A'}

Instructions:
1. Replace forbidden phrases with suggested alternatives
2. Adjust wording to match brand tone
3. PRESERVE all facts, numbers, and core message
4. DO NOT add or remove information
5. DO NOT change the meaning in any way

Rewritten content (style-only changes):"""

        response = await self.llm.ainvoke(prompt)
        rewritten = response.content if hasattr(response, 'content') else str(response)
        
        return rewritten.strip()


async def execute_with_compliance_and_preservation(
    generated_content: str,
    voice_profile: Dict,
    enforcement_mode: str = "strict"
) -> Dict:
    """
    Execute content generation with compliance checking and semantic preservation.
    
    Args:
        generated_content: Content to validate
        voice_profile: Brand voice profile
        enforcement_mode: "strict" (block non-compliant) or "advisory" (warn only)
    
    Returns:
        Dict with:
        - final_content: Compliant content (or original if advisory)
        - violations: List of violations found
        - was_rewritten: bool
        - semantic_similarity: float (if rewritten)
        - enforcement_action: str
    """
    from core.voice.nuance_detector import validate_voice_compliance
    
    # Check compliance
    result = await validate_voice_compliance(generated_content, voice_profile)
    
    if not result["is_compliant"]:
        if enforcement_mode == "strict":
            # Attempt rewrite with semantic preservation
            guard = SemanticPreservationGuard()
            
            try:
                rewritten = await guard.rewrite_with_semantic_preservation(
                    generated_content,
                    result["violations"],
                    voice_profile
                )
                
                # Calculate final similarity
                original_emb = guard.embedder.embed_query(generated_content)
                rewritten_emb = guard.embedder.embed_query(rewritten)
                similarity = guard._cosine_similarity(original_emb, rewritten_emb)
                
                return {
                    "final_content": rewritten,
                    "violations": result["violations"],
                    "was_rewritten": True,
                    "semantic_similarity": round(similarity, 3),
                    "enforcement_action": "REWRITTEN - violations fixed, meaning preserved"
                }
            
            except RewriteViolationError as e:
                # Rewrite failed
                return {
                    "final_content": None,
                    "violations": result["violations"],
                    "was_rewritten": False,
                    "semantic_similarity": None,
                    "enforcement_action": f"BLOCKED - {str(e)}"
                }
        
        else:  # advisory mode
            return {
                "final_content": generated_content,  # Return original
                "violations": result["violations"],
                "was_rewritten": False,
                "semantic_similarity": None,
                "enforcement_action": "WARNING - violations flagged but content returned"
            }
    
    # No violations
    return {
        "final_content": generated_content,
        "violations": [],
        "was_rewritten": False,
        "semantic_similarity": None,
        "enforcement_action": "APPROVED - no violations"
    }
