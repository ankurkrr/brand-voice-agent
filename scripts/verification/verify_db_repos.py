
import asyncio
import uuid
import json
from data.repos.brands import BrandsRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from data.repos.content_briefs import ContentBriefsRepo
from data.db.session import get_pool

async def test_repos():
    print("Starting Repo Verification...")
    
    # Generate unique brand ID
    brand_id = str(uuid.uuid4())
    brand_name = f"Test Brand {brand_id[:8]}"
    
    print(f"Creating Brand: {brand_name} ({brand_id})")
    try:
        brand = await BrandsRepo.create_brand_with_id(brand_id, brand_name)
        print("Brand Created:", brand)
    except Exception as e:
         # Depending on repo implementation, create_brand_with_id might not exist or work differently
         # Fallback to create_brand if needed, but we want specific ID
         print(f"Error creating brand: {e}")
         # Attempt fallback
         # brand = await BrandsRepo.create_brand(brand_name)
         # brand_id = brand['brand_id']
         return

    # Create Voice Profile Data
    profile_data = {
        "system_prompt": "You are a helpful assistant.",
        "rules": {
            "dos": ["Be nice"],
            "donts": ["Be mean"],
            "tone": {"primary": "Friendly"}
        },
        "style_metrics": {"avg_sentence_len": 10},
        "dimensional_scores": {"Humor": 0.5},
        "embedding_meta": {}
    }
    
    print("\nSaving Voice Profile...")
    saved_profile = await VoiceProfilesRepo.save_profile(brand_id, profile_data)
    print("Saved Profile:", saved_profile)
    profile_id = saved_profile['id']
    
    print("\nFetching Voice Profile by Brand ID...")
    fetched_profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
    if fetched_profile:
        print("✅ Fetched Profile Success:", fetched_profile['id'])
    else:
        print("❌ Fetched Profile FAILED: Returned None")
        
    
    # Create Content Brief
    brief_data = {
        "target_audience": "Developers",
        "h2_outline": ["Intro", "Body", "Conclusion"]
    }
    
    print("\nSaving Content Brief...")
    saved_brief = await ContentBriefsRepo.insert_content_brief(
        brand_id=brand_id,
        voice_profile_id=profile_id,
        topic="Test Topic",
        content_brief_data=brief_data
    )
    print("Saved Brief Result:", saved_brief)
    
    print("\nFetching Content Briefs by Brand ID...")
    briefs = await ContentBriefsRepo.fetch_content_briefs_by_brand_id(brand_id)
    print(f"Found {len(briefs)} briefs")
    if len(briefs) > 0:
        print("✅ Brief Fetch Success")
    else:
        print("❌ Brief Fetch FAILED")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_repos())
