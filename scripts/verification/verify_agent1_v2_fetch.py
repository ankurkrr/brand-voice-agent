
import asyncio
import uuid
import json
from data.repos.brands import BrandsRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from core.agents.v2.agent1_voice import run_agent1
from data.db.session import get_pool

import sys

async def verify_v2_fetch():
    with open("verify_output.txt", "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()
        
        log("="*50)
        log("VERIFYING AGENT 1 V2 GOLDEN RECORD FETCH")
        log("="*50)
        
        # 1. Setup Data
        brand_id = str(uuid.uuid4())
        brand_name = f"V2 Test Brand {brand_id[:8]}"
        
        log(f"\n[SETUP] Creating Brand: {brand_name}")
        try:
            await BrandsRepo.create_brand_with_id(brand_id, brand_name)
        except:
            # Fallback if specific repo method differs
            log("Repo create_brand_with_id mismatch, trying manual insert...")
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("INSERT INTO brands (id, brand_id, name) VALUES ($1, $2, $3)", str(uuid.uuid4()), brand_id, brand_name)

        log("[SETUP] Saving V1 Voice Profile...")
        profile_data = {
            "system_prompt": "You are a VERIFIED V1 profile.",
            "rules": {"dos": ["Be verified"], "donts": [], "tone": "TestTone"},
            "status": "active"
        }
        # Save a profile (simulating Agent 1 V1 completion)
        saved = await VoiceProfilesRepo.save_profile(brand_id, profile_data)
        log(f"[SETUP] Profile Saved: v{saved['version']}")

        # 2. Test Success Case
        log("\n[TEST 1] Calling Agent 1 V2 with brand_id...")
        try:
            result = await run_agent1(brand_id=brand_id)
            
            log(f"✅ Result returned: {result.get('profile_id')}")
            log(f"   Is V2? {result.get('is_v2')}")
            log(f"   Source: {result.get('fetch_source')}")
            
            # Verify Content
            if result['system_prompt'] == "You are a VERIFIED V1 profile.":
                log("✅ System Prompt Matches Golden Record")
            else:
                log("❌ System Prompt Mismatch!")
                
        except Exception as e:
            log(f"❌ unexpected error: {e}")
            import traceback
            traceback.print_exc()

        # 3. Test Failure Case (Missing Brand ID)
        log("\n[TEST 2] Calling Agent 1 V2 WITHOUT brand_id...")
        try:
            await run_agent1(brand_id=None)
            log("❌ FAILED: Should have raised ValueError")
        except ValueError as e:
            log(f"✅ Success: Raised expected ValueError: {e}")
        except Exception as e:
            log(f"❌ Wrong exception type: {type(e)}")

        log("\n" + "="*50)
        log("VERIFICATION COMPLETE")
        log("="*50)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(verify_v2_fetch())
