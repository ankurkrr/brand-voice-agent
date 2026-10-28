
import sys
import os

LOG_FILE = "debug_granular.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

log("1. Starting Script")

try:
    import asyncio
    import uuid
    log("2. Imports Basic Success")
    
    from data.repos.voice_profiles import VoiceProfilesRepo
    from core.agents.v2.agent1_voice import run_agent1
    log("3. Imports Project Success")

    async def main():
        log("4. Inside Main")
        try:
            brand_id = str(uuid.uuid4())
            log(f"5. Generated Brand ID: {brand_id}")
            
            # Skip actual DB call if it's the crash cause, just test import first
            # But we want to test correct failure for missing brand
            
            try:
                log("6. Testing run_agent1 with NO brand_id")
                await run_agent1(brand_id=None)
            except ValueError as e:
                log(f"7. Success: Caught Expected Error: {e}")
            except Exception as e:
                log(f"7. Failed: Wrong Error: {e}")

            log("8. Test Complete")

        except Exception as e:
            log(f"Error in Main: {e}")

    if __name__ == "__main__":
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main()) 

except Exception as e:
    log(f"CRITICAL FAILURE: {e}")
