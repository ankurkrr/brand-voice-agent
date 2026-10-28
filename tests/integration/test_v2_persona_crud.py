
import pytest
import uuid
from core.voice.persona_manager import PersonaManager, PersonaConflictError
from core.voice.persona_resolver import list_personas_by_brand, resolve_effective_persona

# Mock data
TEST_BRAND_ID = f"test-brand-{uuid.uuid4()}"
TEST_PERSONA_NAME = "Test CEO Persona"
TEST_PROFILE_DATA = {
    "tone": {"primary": "Authoritative", "description": "CEO Voice"},
    "explicit_rules": {
        "dos": ["Be brief"],
        "donts": ["Use jargon"]
    }
}

@pytest.mark.asyncio
async def test_v2_persona_lifecycle():
    """
    Verify complete V2 Persona Lifecycle: Create -> List -> Resolve -> Update -> Delete.
    Ensures operations target the correct 'voice_personas' table.
    """
    
    # 1. CREATE
    print(f"\n[TEST] Creating persona for brand {TEST_BRAND_ID}...")
    persona_id = await PersonaManager.create_persona(
        brand_id=TEST_BRAND_ID,
        persona_name=TEST_PERSONA_NAME,
        profile_data=TEST_PROFILE_DATA,
        dimensional_scores={"Humor": 0.2}
    )
    assert persona_id is not None
    print(f"[TEST] Created persona_id: {persona_id}")

    # 2. LIST (Must find it in voice_personas)
    print("[TEST] Listing personas...")
    personas = await list_personas_by_brand(TEST_BRAND_ID)
    assert len(personas) == 1
    assert personas[0]["persona_id"] == persona_id
    assert personas[0]["persona_name"] == TEST_PERSONA_NAME
    print("[TEST] Verified persona in list.")

    # 3. RESOLVE (Must retrieve from voice_personas)
    print("[TEST] Resolving persona...")
    resolved = await resolve_effective_persona(persona_id)
    assert resolved.persona_id == persona_id
    assert resolved.tone["primary"] == "Authoritative"
    print("[TEST] Resolved correctly.")

    # 4. UPDATE
    print("[TEST] Updating persona name...")
    new_name = "Updated CEO Persona"
    success = await PersonaManager.update_persona(
        persona_id=persona_id,
        persona_name=new_name
    )
    assert success is True
    
    # Verify update
    updated_list = await list_personas_by_brand(TEST_BRAND_ID)
    assert updated_list[0]["persona_name"] == new_name
    print("[TEST] Update verified.")

    # 5. DELETE
    print("[TEST] Deleting persona...")
    del_success = await PersonaManager.delete_persona(persona_id)
    assert del_success is True
    
    # Verify deletion
    final_list = await list_personas_by_brand(TEST_BRAND_ID)
    assert len(final_list) == 0
    print("[TEST] Deletion verified.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
