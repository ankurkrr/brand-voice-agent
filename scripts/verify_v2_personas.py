
import asyncio
import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

from data.db.session import get_pool
from core.voice.persona_manager import PersonaManager
from core.voice.persona_resolver import list_personas_by_brand

async def verify_default_personas():
    print("Starting Verification...")
    pool = await get_pool()
    
    brand_id = None
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Get a random brand
            await cursor.execute("SELECT id FROM brands LIMIT 1")
            row = await cursor.fetchone()
            if row:
                brand_id = row[0]
    
    if not brand_id:
        print("No brands found in DB. Cannot verify.")
        return

    print(f"Using Brand ID: {brand_id}")
    
    # 1. Ensure Defaults
    print("Ensuring default personas...")
    await PersonaManager.ensure_default_personas(brand_id)
    
    # 2. List Personas
    print("Listing personas...")
    personas = await list_personas_by_brand(brand_id)
    
    print(f"Found {len(personas)} personas.")
    
    expected_keys = {"brand_default", "ceo", "marketing_manager", "support_lead"}
    found_keys = set()
    
    for p in personas:
        # Check DB directly for key if not in list output (list output might be partial)
        # But wait, I updated list_personas_by_brand? NO, I updated `resolve_effective_persona` and `get_persona`.
        # `list_personas_by_brand` was NOT updated to return `persona_key`.
        # I should assume `ensure` worked if count >= 4.
        # Logic in `ensure_default_personas` checks keys. 
        # So I will trust my code but I'll update correct verification logic below.
        pass

    # Re-query DB to check keys
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT persona_key, persona_name FROM voice_personas WHERE brand_id = %s", (brand_id,))
            rows = await cursor.fetchall()
            for r in rows:
                if r[0]:
                    found_keys.add(r[0])
                print(f" - {r[1]} (Key: {r[0]})")

    missing = expected_keys - found_keys
    if missing:
        print(f"FAILED: Missing keys: {missing}")
    else:
        print("SUCCESS: All default personas found.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_default_personas())
