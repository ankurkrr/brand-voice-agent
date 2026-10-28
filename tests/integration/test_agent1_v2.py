import asyncio
import uuid
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from data.repos.brands import BrandsRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from core.agents.v2.agent1_voice import run_agent1
from data.db.session import get_pool

async def test_agent1_v2_integration():
    with open("integration_test_result.txt", "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()

        log("="*60)
        log("TESTING AGENT 1 V2 INTEGRATION (GOLDEN RECORD FETCH)")
        log("="*60)

        # 1. Setup: Create Brand & V1 Profile
        brand_id = str(uuid.uuid4())
        brand_name = f"IntegrationTest_{brand_id[:8]}"
        log(f"\n[SETUP] Creating Brand: {brand_name}")
        
        try:
            await BrandsRepo.create_brand_with_id(brand_id, brand_name)
        except:
            # Manual fallback
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("INSERT INTO brands (id, brand_id, name) VALUES ($1, $2, $3)", str(uuid.uuid4()), brand_id, brand_name)

        log("[SETUP] Creating V1 Golden Record...")
        v1_rules = {
            "dos": ["Be precise", "Use active voice"], 
            "donts": ["No fluff"], 
            "tone": "Authoritative"
        }
        v1_prompt = "You are the Golden Record Reference."
        
        profile_data = {
            "system_prompt": v1_prompt,
            "rules": v1_rules,
            "status": "active",
            "tone": "Authoritative" 
        }
        
        saved_profile = await VoiceProfilesRepo.save_profile(brand_id, profile_data)
        log(f"[SETUP] V1 Profile Saved: ID={saved_profile['id']} Version={saved_profile['version']}")

        # 2. Execute: Run Agent 1 V2
        log("\n[EXECUTE] Running Agent 1 V2 (should fetch from DB)...")
        try:
            # V2 Call - Should only need brand_id
            v2_result = await run_agent1(brand_id=brand_id)
            
            log("\n[VERIFY] Inspecting Result...")
            
            # 3. Assertions
            # check basic fields
            assert v2_result['brand_id'] == brand_id, "Brand ID mismatch"
            assert v2_result['profile_id'] == saved_profile['id'], "Profile ID mismatch"
            assert v2_result['is_v2'] is True, "Missing is_v2 flag"
            assert v2_result['fetch_source'] == "database_golden_record", "Wrong fetch source"
            
            # Check Golden Record Integrity
            log(f"   System Prompt: {v2_result['system_prompt']}")
            assert v2_result['system_prompt'] == v1_prompt, "System prompt does not match V1 record"
            
            # Check Rules JSON parsing
            log(f"   Rules: {v2_result['explicit_rules']}")
            assert v2_result['explicit_rules']['dos'][0] == "Be precise", "Rules data corrupted"
            
            log("\n✅ TEST PASSED: Agent 1 V2 correctly fetched the Golden Record.")
            
        except ValueError as e:
            log(f"❌ TEST FAILED: ValueError: {e}")
        except AssertionError as e:
            log(f"❌ TEST FAILED: Assertion Error: {e}")
        except Exception as e:
            log(f"❌ TEST FAILED: Unexpected Error: {e}")
            import traceback
            traceback.print_exc(file=f)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_agent1_v2_integration())
