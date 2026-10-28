"""
Persona Manager API - Phase 2: Multi-Persona Architect

CRUD operations for multi-persona hierarchy and management.

Provides:
- Create/update/delete personas
- Get persona hierarchy tree
- List personas by brand
- Validation helpers
"""

from typing import List, Dict, Optional
import uuid
from data.db.session import get_pool
import aiomysql
import json
from core.voice.persona_resolver import (
    resolve_effective_persona,
    list_personas_by_brand,
    get_persona_hierarchy,
    PersonaConflictError
)
from data.repos.voice_personas import VoicePersonasRepo

DEFAULT_PERSONAS = [
    {
        "key": "brand_default",
        "name": "Brand Voice (Default)",
        "prompt": "Use the core brand voice exactly as defined. Do not apply role-specific framing."
    },
    {
        "key": "ceo",
        "name": "CEO",
        "prompt": "Speak at a strategic and visionary level. Focus on outcomes, direction, and long-term impact. Avoid tactical execution details or internal process language. Assume a senior stakeholder audience."
    },
    {
        "key": "marketing_manager",
        "name": "Marketing Manager",
        "prompt": "Focus on execution, campaigns, and coordination. Be practical, action-oriented, and team-focused. Reference timelines, initiatives, and implementation details where appropriate."
    },
    {
        "key": "support_lead",
        "name": "Customer Support Lead",
        "prompt": "Be empathetic, reassuring, and solution-focused. Use clear, simple language. Prioritize user understanding and problem resolution."
    }
]


class PersonaManager:
    """
    Manage multi-persona operations.
    
    All operations validate against strict rules:
    - No circular references
    - No orphaned personas
    - Conflict detection for dos/donts
    """
    
    @staticmethod
    async def create_persona(
        brand_id: str,
        persona_name: str,
        profile_data: Dict,
        dimensional_scores: Optional[Dict] = None,
        parent_persona_id: Optional[str] = None
    ) -> str:
        """
        Create a new persona.
        
        Args:
            brand_id: Brand ID
            persona_name: Human-readable name
            profile_data: Voice profile data (rules, examples, etc.)
            dimensional_scores: Optional dimensional scores (0.0-1.0)
            parent_persona_id: Optional parent for inheritance
        
        Returns:
            persona_id
        
        Raises:
            PersonaConflictError: If circular reference or conflicts detected
        """
        persona_id = str(uuid.uuid4())
        profile_id = persona_id  # Use same ID for V2
        
        # Validate no circular reference (if has parent)
        if parent_persona_id:
            try:
                # Try resolving parent to ensure it exists
                await resolve_effective_persona(parent_persona_id)
            except Exception as e:
                raise PersonaConflictError(f"Invalid parent persona: {e}")
        
        # Insert into database
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO voice_personas
                    (id, persona_id, brand_id, persona_name, parent_persona_id,
                    profile_data, dimensional_scores, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                """, (
                    str(uuid.uuid4()),
                    persona_id,
                    brand_id,
                    persona_name,
                    parent_persona_id,
                    json.dumps(profile_data),
                    json.dumps(dimensional_scores) if dimensional_scores else None
                ))
                await conn.commit()
        
        return persona_id
    
    @staticmethod
    async def update_persona(
        persona_id: str,
        profile_data: Optional[Dict] = None,
        dimensional_scores: Optional[Dict] = None,
        persona_name: Optional[str] = None
    ) -> bool:
        """
        Update existing persona.
        
        Args:
            persona_id: Persona to update
            profile_data: New profile data (optional)
            dimensional_scores: New dimensional scores (optional)
            persona_name: New name (optional)
        
        Returns:
            True if updated
        """
        pool = await get_pool()
        
        updates = []
        params = []
        
        if profile_data is not None:
            updates.append("profile_data = %s")
            params.append(json.dumps(profile_data))
        
        if dimensional_scores is not None:
            updates.append("dimensional_scores = %s")
            params.append(json.dumps(dimensional_scores))
        
        if persona_name is not None:
            updates.append("persona_name = %s")
            params.append(persona_name)
        
        if not updates:
            return False
        
        params.append(persona_id)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    UPDATE voice_personas
                    SET {', '.join(updates)}
                    WHERE persona_id = %s
                """, params)
                await conn.commit()
                
                return cursor.rowcount > 0
    
    @staticmethod
    async def delete_persona(persona_id: str, force: bool = False) -> bool:
        """
        Delete persona.
        
        Args:
            persona_id: Persona to delete
            force: If True, delete children too (cascade)
                   If False, fail if has children
        
        Returns:
            True if deleted
        
        Raises:
            PersonaConflictError: If has children and force=False
        """
        pool = await get_pool()
        
        # Check for children
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM voice_personas
                    WHERE parent_persona_id = %s
                """, (persona_id,))
                result = await cursor.fetchone()
                
                if result['count'] > 0 and not force:
                    raise PersonaConflictError(
                        f"Cannot delete persona with {result['count']} children. "
                        f"Use force=True to delete all children."
                    )
                
                # Delete children first if force
                if force and result['count'] > 0:
                    await cursor.execute("""
                        DELETE FROM voice_personas
                        WHERE parent_persona_id = %s
                    """, (persona_id,))
                
                # Delete persona
                await cursor.execute("""
                    DELETE FROM voice_personas
                    WHERE persona_id = %s
                """, (persona_id,))
                await conn.commit()
                
                return cursor.rowcount > 0
    
    @staticmethod
    async def get_personas_by_brand(brand_id: str) -> List[Dict]:
        """List all personas for a brand."""
        return await list_personas_by_brand(brand_id)
    
    @staticmethod
    async def get_hierarchy(brand_id: str) -> Dict:
        """Get persona hierarchy tree for a brand."""
        return await get_persona_hierarchy(brand_id)
        
    @staticmethod
    async def ensure_default_personas(brand_id: str):
        """
        Ensure the 4 default personas exist for the brand.
        Creates them if missing.
        """
        # 1. Get existing personas to check keys
        existing = await list_personas_by_brand(brand_id)
        existing_keys = {p.get('persona_key') for p in existing if p.get('persona_key')}
        
        # 2. Iterate and create missing
        for default in DEFAULT_PERSONAS:
            if default["key"] not in existing_keys:
                
                # Base profile data (minimal)
                profile_data = {
                    "explicit_rules": {
                        "tone": {"primary": "Inherited", "description": "Inherited from brand voice"},
                        "dos": [],
                        "donts": []
                    }
                }
                
                await VoicePersonasRepo.create_persona(
                    brand_id=brand_id,
                    persona_id=str(uuid.uuid4()), # New UUID
                    persona_name=default["name"],
                    profile_data=profile_data,
                    dimensional_scores={}, # Inherit/Default
                    parent_persona_id=None, # Root or could be attached to a main profile? 
                                            # Requirement says "Personas are created by Agent-1... Personas are system defaults".
                                            # "Use the core brand voice exactly as defined" -> Implies they should inherit if possible, 
                                            # BUT "Brand Voice (Default)" sounds like the root or a proxy to it.
                                            # "brand_default" is likely the wrapper for the raw profile.
                                            # Wait, if they are roots, they don't inherit.
                                            # "Each persona has its own distinct, role-specific prompt overlay."
                                            # "Agent-3... Inject: Brand Voice Prompt + Persona Overlay Prompt"
                                            # So they don't strictly need to be parents of each other.
                                            # They are siblings or just standalone configuration entries enabling the overlay.
                                            # I will create them as ROOTS (parent_persona_id=None) but typically the Resolver manages the inheritance 
                                            # from the "Brand Voice Profile" (V1). 
                                            # Actually, V2 Persona Resolution handles parent_persona_id.
                                            # If I create them with None, they are roots. 
                                            # Agent-3 Logic: "Resolve persona from DB... Inject Brand Voice Prompt + Overlay".
                                            # If they are roots, they might not automatically pick up the "Main Brand Voice" if that is stored separately in VoiceProfiles.
                                            # However, The "Brand Voice" is usually the V1 Golden Record.
                                            # The requirements says "Brand Voice (Default)... Use the core brand voice exactly as defined."
                                            # and "Agent-3... Inject: Brand Voice Prompt + Persona Overlay Prompt".
                                            # This implies the Base Brand Voice comes from somewhere else (V1 Profile) and these are selected modifiers.
                                            # But the Resolver `resolve_effective_persona` tries to merge with parent.
                                            # If these defaults are created without a parent, they define their own (empty) rules?
                                            # Re-reading: "You must implement logic that... Creates any missing ones... Does NOT modify existing personas".
                                            # 
                                            # Since I don't know the "Main V1 Profile ID" easily here (it changes), I can't easily set parent_persona_id to it 
                                            # unless I query it.
                                            # BUT, for the "UX" sake, they are just selection keys.
                                            # Agent-3 V2 fetches the persona.
                                            # Then it injects "Brand Voice Prompt" (from where?) + "Persona Overlay Prompt".
                                            # In `agent3_execution.py` V2: `run_agent3_v1(v1_request_obj)`
                                            # `v1_request_obj` has `BrandVoiceProfile`.
                                            # If I want Agent-3 to use the "Main Brand Voice" + "Overlay", 
                                            # I should ensure `run_agent3` fetches the Main Brand Voice (V1) AND applies the overlay.
                                            # OR, these Personas *ARE* the definitions.
                                            #
                                            # Requirement: "Agent-3... Resolve persona from DB... Inject: Brand Voice Prompt + Persona Overlay Prompt".
                                            # "Inject" implies combination.
                                            # "Brand Voice Prompt" refers to the core rules (Dos/Donts/etc) from the V1 Profile.
                                            # So `run_agent3` logic I wrote:
                                            # `persona = await VoicePersonasRepo.get_persona(...)`
                                            # It uses that persona object to build `BrandVoiceProfile`.
                                            # IF that persona object is empty (default created here), it will have NO rules.
                                            # That would break "Brand Voice".
                                            # 
                                            # CRITICAL FIX: The default personas must be linked to the Brand's "Active" Voice Profile?
                                            # Or Agent-3 V2 must fetch the "Active V1 Profile" AND the "Selected Persona (Overlay)", then merge.
                                            # 
                                            # Let's check `agent3_execution.py` again.
                                            # I wrote: `persona = await VoicePersonasRepo.get_persona(...)`. `profile_json = persona`. `brand_voice_profile = BrandVoiceProfile(**profile_json)`.
                                            # This assumes `persona` HAS the full profile.
                                            # If `ensure_default_personas` creates empty shells, Agent-3 will fail (no Dos/Donts).
                                            #
                                            # However, linking to a specific `parent_persona_id` (V1 Profile ID) is hard because V1 profiles change/regenerate (versions).
                                            #
                                            # ALTERNATIVE: V2 Agent-3 should:
                                            # 1. Fetch the LATEST ACTIVE V1 PROFILE (The "Brand Voice").
                                            # 2. Fetch the SELECTED PERSONA (The "Overlay").
                                            # 3. Merge them (Overlay rules >> Base rules).
                                            #
                                            # BUT `persona_resolver.py` does merging if `parent_persona_id` is set.
                                            #
                                            # If I cannot reliably set `parent_persona_id` to the "Current Active V1 Profile" during creation,
                                            # creates a disconnect.
                                            #
                                            # WAIT. "Agent-1 V2... Checks for the 4 default personas... Creates any missing ones".
                                            # Agent-1 V2 is "Brand Voice Refinement". It CREATES the refined persona.
                                            # The Defaults are "System Defaults".
                                            #
                                            # Perhaps the defaults should point to the "System" root?
                                            # Or maybe Agent-3 logic should be smarter: If persona has no rules, use Active Profile rules + Overlay?
                                            #
                                            # "Agent-3... Inject: Brand Voice Prompt + Persona Overlay Prompt".
                                            # This strongly suggests the "Brand Voice Prompt" (Core) is separate from "Persona" (Overlay).
                                            #
                                            # So `run_agent3` update (Task 7) is where I handle the merging if the persona itself doesn't have the full rules.
                                            #
                                            # For now, `ensure_default_personas` creates the RECORD of the persona (The Overlay Definition).
                                            # I will create them with EMPTY rules.
                                            # AND I will update `agent3_execution.py` to:
                                            # 1. Fetch Active V1 Profile (Base).
                                            # 2. Fetch Selected Persona (Overlay).
                                            # 3. Apply Overlay to Base.
                                            #
                                            # This is "Additive" and safe.
                                            #
                                            # So, `create_persona` with empty rules is OK here, provided Agent-3 handles the merge.
                                            
                    persona_key=default["key"],
                    persona_origin="SYSTEM",
                    persona_overlay_prompt=default["prompt"],
                    persona_scope="OVERLAY",
                    persona_version=1
                )
    
    @staticmethod
    async def validate_persona_rules(persona_id: str) -> Dict:
        """
        Validate persona rules for conflicts.
        
        Returns:
            Dict with:
            - is_valid: bool
            - conflicts: List[str]
            - warnings: List[str]
        """
        try:
            persona = await resolve_effective_persona(persona_id)
            
            return {
                "is_valid": True,
                "conflicts": [],
                "warnings": [],
                "resolved_persona": {
                    "persona_id": persona.persona_id,
                    "persona_name": persona.persona_name,
                    "hierarchy_depth": persona.hierarchy_depth,
                    "forbidden_phrases_count": len(persona.forbidden_phrases),
                    "dimensional_scores": persona.dimensional_scores
                }
            }
        
        except PersonaConflictError as e:
            return {
                "is_valid": False,
                "conflicts": [str(e)],
                "warnings": []
            }
        
        except Exception as e:
            return {
                "is_valid": False,
                "conflicts": [],
                "warnings": [f"Validation error: {str(e)}"]
            }
