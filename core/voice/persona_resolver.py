"""
Persona Resolution Module - Phase 2: Multi-Persona Architect

This module implements the MANDATORY resolve_effective_persona() function with
circular chain detection (CRITICAL FIX #2).

STRICT ENFORCEMENT:
- This is the ONLY way to load personas for agent consumption
- Direct database reads from agents are PROHIBITED
- Multi-node circular chains (A→B→C→A) are detected at application level
- All inherited rules are merged according to strict hierarchy
"""

from typing import Dict, Set, Optional, List
from dataclasses import dataclass
import json
from data.db.session import get_pool
import aiomysql


# Custom exceptions
class PersonaNotFoundError(ValueError):
    """Raised when persona_id does not exist in database."""
    pass


class PersonaConflictError(ValueError):
    """Raised when circular inheritance detected or rules contradict."""
    pass


@dataclass
class ResolvedPersona:
    """
    Immutable resolved persona with all inherited rules merged.
    
    This is what agents receive - never raw database records.
    """
    persona_id: str
    persona_name: str
    brand_id: str
    
    # Merged rules (parent + child)
    tone: Dict
    dos: List[str]
    donts: List[str]
    forbidden_phrases: List[str]
    preferred_vocabulary: List[str]
    
    # Child overrides (dimensional scores)
    dimensional_scores: Dict[str, float]
    
    # Style metrics (for reference)
    style_metrics: Dict
    
    # Examples (from ChromaDB)
    examples: List[Dict]
    
    # Hierarchy metadata
    parent_persona_id: Optional[str]
    hierarchy_depth: int  # 0 = root, 1 = child, 2 = grandchild, etc.

    # Original profile data (for audit)
    raw_profile_data: Dict
    
    # V2 New Fields
    persona_key: Optional[str] = None
    persona_origin: str = "SYSTEM"
    persona_overlay_prompt: Optional[str] = None
    persona_scope: str = "OVERLAY"
    persona_version: int = 1


async def resolve_effective_persona(
    persona_id: str,
    visited: Optional[Set[str]] = None
) -> ResolvedPersona:
    """
    MANDATORY: Only way to load personas for agent consumption.
    
    CRITICAL FIX #2: Detects multi-node circular chains (A→B→C→A).
    Database constraints only prevent self-reference (A→A).
    Application code MUST detect complex cycles.
    
    Args:
        persona_id: Persona to resolve
        visited: Set of visited persona IDs (for cycle detection)
    
    Returns:
        ResolvedPersona with inherited rules merged per strict hierarchy:
        - forbidden_phrases = UNION(parent + child)
        - dimensional_scores = child overrides parent per dimension
        - dos/donts = UNION with conflict detection
    
    Raises:
        PersonaConflictError: If circular inheritance detected (e.g., A→B→C→A)
        PersonaNotFoundError: If persona_id invalid
    
    Example:
        >>> persona = await resolve_effective_persona("persona_123")
        >>> # Use persona.forbidden_phrases, persona.dimensional_scores, etc.
        >>> # Never access raw database records directly
    """
    if visited is None:
        visited = set()
    
    # CRITICAL: Cycle detection
    if persona_id in visited:
        chain = ' → '.join(visited) + f' → {persona_id}'
        raise PersonaConflictError(
            f"Circular persona inheritance detected: {chain}\n"
            f"This violates strict inheritance rules. "
            f"Each persona must have a clear parent-child hierarchy."
        )
    
    visited.add(persona_id)
    
    # Load persona from database
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT * FROM voice_personas WHERE persona_id = %s
            """, (persona_id,))
            persona_row = await cursor.fetchone()
    
    if persona_row is None:
        # Try fallback: V1 profiles use profile_id, not persona_id
        # Query voice_profiles_human (V1) joined with voice_profiles_machine (V2)
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT h.profile_id, h.brand_id, h.system_prompt, h.explicit_rules,
                           h.version, h.status, h.created_at,
                           m.dimensional_scores, m.implicit_rules
                    FROM voice_profiles_human h
                    LEFT JOIN voice_profiles_machine m ON h.profile_id = m.profile_id
                    WHERE h.profile_id = %s
                    LIMIT 1
                """, (persona_id,))
                v1_row = await cursor.fetchone()
        
        if v1_row is not None:
            # Build a persona-compatible dict from V1 profile columns
            explicit_rules = v1_row.get('explicit_rules', '{}')
            if isinstance(explicit_rules, str):
                explicit_rules = json.loads(explicit_rules)
            
            dim_scores = v1_row.get('dimensional_scores')
            if isinstance(dim_scores, str):
                dim_scores = json.loads(dim_scores) if dim_scores else None
            
            persona_row = {
                'persona_id': v1_row['profile_id'],
                'persona_name': 'Primary',
                'brand_id': v1_row['brand_id'],
                'parent_persona_id': None,
                'profile_data': json.dumps({'explicit_rules': explicit_rules}),
                'dimensional_scores': json.dumps(dim_scores) if dim_scores else None,
                'status': v1_row.get('status', 'active'),
            }
        
        if persona_row is None:
            raise PersonaNotFoundError(
                f"Persona '{persona_id}' not found. "
                f"Please check the persona_id or use list_personas() to see available personas."
            )
    
    # Parse profile_data JSON
    profile_data = persona_row['profile_data']
    if isinstance(profile_data, str):
        profile_data = json.loads(profile_data)
    
    # Recursive resolution if parent exists
    parent_persona_id = persona_row.get('parent_persona_id')
    
    if parent_persona_id:
        # Recursively resolve parent (will detect cycles)
        parent_persona = await resolve_effective_persona(parent_persona_id, visited)
        
        # Merge child with parent
        resolved = _merge_with_parent(persona_row, profile_data, parent_persona)
    else:
        # Root persona (no parent)
        resolved = _create_root_persona(persona_row, profile_data)
    
    return resolved


def _merge_with_parent(
    child_row: Dict,
    child_profile_data: Dict,
    parent_persona: ResolvedPersona
) -> ResolvedPersona:
    """
    Merge child persona with resolved parent according to strict hierarchy.
    
    STRICT RULES:
    - forbidden_phrases: UNION (child CANNOT remove parent's forbidden phrases)
    - dimensional_scores: Child overrides parent per dimension
    - dos/donts: UNION with conflict detection
    """
    child_rules = child_profile_data.get('explicit_rules', {})
    
    # UNION: Forbidden phrases (child adds to parent, cannot remove)
    merged_forbidden = list(set(
        parent_persona.forbidden_phrases +
        child_rules.get('forbidden_phrases', [])
    ))
    
    # UNION: Dos (child adds to parent)
    merged_dos = list(set(
        parent_persona.dos +
        child_rules.get('dos', [])
    ))
    
    # UNION: Donts (child adds to parent)
    merged_donts = list(set(
        parent_persona.donts +
        child_rules.get('donts', [])
    ))
    
    # Check for conflicts (DO vs DON'T contradiction)
    conflicts = _detect_rule_conflicts(merged_dos, merged_donts)
    if conflicts:
        raise PersonaConflictError(
            f"Child persona '{child_row['persona_name']}' contradicts parent rules:\n" +
            "\n".join([f"  - {c}" for c in conflicts])
        )
    
    # UNION: Preferred vocabulary
    merged_vocab = list(set(
        parent_persona.preferred_vocabulary +
        child_rules.get('preferred_vocabulary', [])
    ))
    
    # OVERRIDE: Dimensional scores (child can override parent per dimension)
    child_scores = child_row.get('dimensional_scores')
    if isinstance(child_scores, str):
        child_scores = json.loads(child_scores) if child_scores else {}
    elif child_scores is None:
        child_scores = {}
    
    merged_dimensions = parent_persona.dimensional_scores.copy()
    merged_dimensions.update(child_scores)  # Child overrides parent
    
    # INHERIT: Tone (child can add secondary tones but not change primary)
    child_tone = child_rules.get('tone', {})
    merged_tone = {
        "primary": parent_persona.tone.get("primary"),  # Cannot override
        "secondary": list(set(
            parent_persona.tone.get("secondary", []) +
            child_tone.get("secondary", [])
        )),
        "description": child_tone.get("description", parent_persona.tone.get("description"))
    }
    
    return ResolvedPersona(
        persona_id=child_row['persona_id'],
        persona_name=child_row['persona_name'],
        brand_id=child_row['brand_id'],
        tone=merged_tone,
        dos=merged_dos,
        donts=merged_donts,
        forbidden_phrases=merged_forbidden,
        preferred_vocabulary=merged_vocab,
        dimensional_scores=merged_dimensions,
        style_metrics=child_profile_data.get('implicit_rules', {}),
        examples=child_profile_data.get('examples', []),
        parent_persona_id=parent_persona.persona_id,
        hierarchy_depth=parent_persona.hierarchy_depth + 1,
        
        # V2 New Fields (Child overrides)
        persona_key=child_row.get('persona_key'),
        persona_origin=child_row.get('persona_origin', 'SYSTEM'),
        persona_overlay_prompt=child_row.get('persona_overlay_prompt'),
        persona_scope=child_row.get('persona_scope', 'OVERLAY'),
        persona_version=child_row.get('persona_version', 1),
        
        raw_profile_data=child_profile_data
    )


def _create_root_persona(persona_row: Dict, profile_data: Dict) -> ResolvedPersona:
    """Create ResolvedPersona for root persona (no parent)."""
    rules = profile_data.get('explicit_rules', {})
    tone = rules.get('tone', {})
    
    # Parse dimensional scores
    dim_scores = persona_row.get('dimensional_scores')
    if isinstance(dim_scores, str):
        dim_scores = json.loads(dim_scores) if dim_scores else {}
    elif dim_scores is None:
        # Default neutral scores if not available
        dim_scores = {
            "Humor": 0.5,
            "Empathy": 0.5,
            "Authority": 0.5,
            "Formality": 0.5,
            "Urgency": 0.5
        }
    
    return ResolvedPersona(
        persona_id=persona_row.get('persona_id') or persona_row['profile_id'],
        persona_name=persona_row.get('persona_name', 'Primary'),
        brand_id=persona_row['brand_id'],
        tone=tone,
        dos=rules.get('dos', []),
        donts=rules.get('donts', []),
        forbidden_phrases=rules.get('forbidden_phrases', []),
        preferred_vocabulary=rules.get('preferred_vocabulary', []),
        dimensional_scores=dim_scores,
        style_metrics=profile_data.get('implicit_rules', {}),
        examples=profile_data.get('examples', []),
        parent_persona_id=None,
        hierarchy_depth=0,
        
        # V2 New Fields
        persona_key=persona_row.get('persona_key'),
        persona_origin=persona_row.get('persona_origin', 'SYSTEM'),
        persona_overlay_prompt=persona_row.get('persona_overlay_prompt'),
        persona_scope=persona_row.get('persona_scope', 'OVERLAY'),
        persona_version=persona_row.get('persona_version', 1),
        
        raw_profile_data=profile_data
    )


def _detect_rule_conflicts(dos: List[str], donts: List[str]) -> List[str]:
    """
    Detect contradictions between DOs and DON'Ts.
    
    Example conflicts:
    - DO: "Use technical terms" vs DON'T: "Avoid jargon"
    - DO: "Be casual" vs DON'T: "Use formal language"
    
    Returns:
        List of conflict descriptions (empty if no conflicts)
    """
    conflicts = []
    
    # Simple keyword-based conflict detection
    # (In production, use embeddings for semantic similarity)
    
    conflict_pairs = [
        (['jargon', 'technical', 'specialized'], ['simple', 'plain', 'accessible']),
        (['formal', 'professional'], ['casual', 'informal', 'friendly']),
        (['active', 'direct'], ['passive']),
        (['long', 'detailed'], ['concise', 'brief', 'short']),
    ]
    
    for do_item in dos:
        do_lower = do_item.lower()
        for dont_item in donts:
            dont_lower = dont_item.lower()
            
            # Check for keyword conflicts
            for keywords_a, keywords_b in conflict_pairs:
                has_a_in_do = any(kw in do_lower for kw in keywords_a)
                has_b_in_dont = any(kw in dont_lower for kw in keywords_b)
                
                has_b_in_do = any(kw in do_lower for kw in keywords_b)
                has_a_in_dont = any(kw in dont_lower for kw in keywords_a)
                
                if (has_a_in_do and has_a_in_dont) or (has_b_in_do and has_b_in_dont):
                    conflicts.append(
                        f"DO: '{do_item}' contradicts DON'T: '{dont_item}'"
                    )
    
    return conflicts


async def list_personas_by_brand(brand_id: str) -> List[Dict]:
    """
    List all personas for a brand (for debugging/admin).
    
    Returns:
        List of dicts with persona_id, persona_name, parent_persona_id
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT persona_id, persona_name, parent_persona_id, created_at, persona_key, persona_origin, status
                FROM voice_personas
                WHERE brand_id = %s
                ORDER BY created_at ASC
            """, (brand_id,))
            personas = await cursor.fetchall()
    
    return personas


async def get_persona_hierarchy(brand_id: str) -> Dict:
    """
    Get persona hierarchy tree for a brand.
    
    Returns:
        Dict representing tree structure with children nested
    """
    personas = await list_personas_by_brand(brand_id)
    
    #Build tree
    persona_map = {p['persona_id']: {**p, 'children': []} for p in personas}
    
    root_personas = []
    for persona in personas:
        if persona['parent_persona_id'] is None:
            root_personas.append(persona_map[persona['persona_id']])
        else:
            parent = persona_map.get(persona['parent_persona_id'])
            if parent:
                parent['children'].append(persona_map[persona['persona_id']])
    
    return {
        "brand_id": brand_id,
        "total_personas": len(personas),
        "hierarchy": root_personas
    }
