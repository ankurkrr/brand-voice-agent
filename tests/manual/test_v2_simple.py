
import asyncio
import uuid
import sys
import os

from data.repos.brands import BrandsRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from core.agents.v2.agent1_voice import run_agent1
from data.db.session import get_pool

async def test_simple():
    with open("v2_test_log.txt", "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(str(msg) + "\n")
            f.flush()

        log("STARTING TEST")
        
        try:
            # 1. Setup
            brand_id = str(uuid.uuid4())
            log(f"Brand ID: {brand_id}")
            
            try:
                await BrandsRepo.create_brand_with_id(brand_id, "TestBrand")
            except:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute("INSERT INTO brands (id, brand_id, name) VALUES ($1, $2, $3)", str(uuid.uuid4()), brand_id, "TestBrand")
            
            # 2. Save V1 Profile
            v1_data = {
                "system_prompt": "GOLDEN RECORD PROMPT",
                "rules": {"dos": ["A"], "donts": ["B"], "tone": "C"},
                "status": "active"
            }
            saved = await VoiceProfilesRepo.save_profile(brand_id, v1_data)
            log(f"Saved Profile: {saved['id']}")
            
            # 3. Call V2
            log("Calling Agent 1 V2...")
            res = await run_agent1(brand_id=brand_id)
            
            log(f"Result: {res['system_prompt']}")
            
            if res['system_prompt'] == "GOLDEN RECORD PROMPT" and res['is_v2'] == True:
                log("SUCCESS: Fetched Golden Record")
            else:
                log("FAILURE: Content Mismatch")
                
        except Exception as e:
            log(f"ERROR: {e}")
            import traceback
            traceback.print_exc(file=f)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_simple())
