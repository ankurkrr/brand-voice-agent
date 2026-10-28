"""
Agent 2 Database Save Diagnostic Script
Run this to test the complete Agent 2 save flow
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Test brand_id from your error earlier
TEST_BRAND_ID = "689182c9-3feb-4949-ac55-f81e693424ba"
TEST_TOPIC = "AI in Healthcare"

async def test_agent2_flow():
    print("=" * 70)
    print("AGENT 2 DATABASE SAVE DIAGNOSTIC")
    print("=" * 70)
    
    # Step 1: Check database connection
    print("\n[STEP 1] Testing database connection...")
    try:
        from data.db.session import get_pool
        pool = await get_pool()
        print("✅ Database pool created")
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Step 2: Check if brand exists
    print(f"\n[STEP 2] Checking if brand {TEST_BRAND_ID} exists...")
    try:
        from data.repos.brands import BrandsRepo
        brand = await BrandsRepo.get_brand_by_id(TEST_BRAND_ID)
        if brand:
            print(f"✅ Brand found: {brand}")
        else:
            print(f"⚠️  Brand NOT found in database")
            print("   Creating brand for testing...")
            brand = await BrandsRepo.create_brand_with_id(TEST_BRAND_ID, "Test Brand")
            print(f"✅ Brand created: {brand}")
    except Exception as e:
        print(f"❌ Brand check failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Check if voice profile exists
    print(f"\n[STEP 3] Checking if voice profile exists for brand {TEST_BRAND_ID}...")
    try:
        from data.repos.voice_profiles import VoiceProfilesRepo
        profile = await VoiceProfilesRepo.get_profile_by_brand_id(TEST_BRAND_ID)
        if profile:
            print(f"✅ Voice profile found: {profile['profile_id']}")
            print(f"   Status: {profile.get('status', 'N/A')}")
        else:
            print(f"⚠️  NO voice profile found for brand {TEST_BRAND_ID}")
            print("   This is why Agent 2 cannot save!")
            print("   Agent 1 must create the voice profile first.")
            return
    except Exception as e:
        print(f"❌ Profile check failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Test Agent 2 brief save
    print(f"\n[STEP 4] Testing Agent 2 content brief save...")
    try:
        from data.repos.content_briefs import ContentBriefsRepo
        
        test_brief_data = {
            "target_audience": "Healthcare professionals",
            "key_takeaways": ["AI improves diagnostics", "ML reduces costs"],
            "seo_keywords": ["AI", "healthcare", "machine learning"],
            "h2_outline": ["Introduction", "AI Applications", "Conclusion"],
            "cta": "Learn more"
        }
        
        result = await ContentBriefsRepo.insert_content_brief(
            brand_id=TEST_BRAND_ID,
            voice_profile_id=profile['profile_id'],
            topic=TEST_TOPIC,
            content_brief_data=test_brief_data,
            fingerprint="test-fingerprint-123"
        )
        
        print(f"✅ Content brief saved successfully!")
        print(f"   Brief ID: {result['id']}")
        print(f"   Brand ID: {result['brand_id']}")
        print(f"   Voice Profile ID: {result['voice_profile_id']}")
        
    except Exception as e:
        print(f"❌ Content brief save failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Verify save by querying database
    print(f"\n[STEP 5] Verifying save by querying database...")
    try:
        briefs = await ContentBriefsRepo.fetch_content_briefs_by_brand_id(TEST_BRAND_ID)
        print(f"✅ Found {len(briefs)} content brief(s) for brand {TEST_BRAND_ID}")
        for brief in briefs:
            print(f"   - Brief ID: {brief.get('brief_id', 'N/A')}")
            print(f"     Topic: {brief.get('topic', 'N/A')}")
            print(f"     Created: {brief.get('created_at', 'N/A')}")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_agent2_flow())
