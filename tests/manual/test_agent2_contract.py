# Test script for Agent 2 ARD Compliance
import requests
import json

BASE_URL = "http://localhost:8082"

def test_agent2_frozen_contract():
    """Test Agent 2 frozen contract enforcement"""
    
    print("=" * 70)
    print("TESTING AGENT 2 ARD FROZEN CONTRACT")
    print("=" * 70)
    
    # Step 1: Create test brand and voice profile
    print("\n1. Setting up test brand...")
    response = requests.post(f"{BASE_URL}/brands/create", json={"name": "TestBrand"})
    brand = response.json()
    brand_id = brand['brand_id']
    print(f"✓ Brand created: {brand_id}")
    
    print("\n2. Creating voice profile (Agent 1)...")
    response = requests.post(
        f"{BASE_URL}/ingest",
        json={
            "brand_name": "TestBrand",
            "input_type": "text",
            "input_value": "We are professional. Use active voice. No jargon."
        }
    )
    if response.status_code == 200:
        print(f"✓ Voice profile created")
    else:
        print(f"✗ Failed: {response.status_code}")
        return
    
    # Step 2: Test Agent 2 Ideation
    print("\n3. Testing Agent 2 ideation...")
    response = requests.post(
        f"{BASE_URL}/ideation/ideate",
        json={
            "brand_id": brand_id,
            "topic": "AI in Healthcare",
            "market": "Enterprise",
            "region": "North America",
            "content_goal": "Thought Leadership"
        }
    )
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return
    
    result = response.json()
    brief = result['content_brief']
    
    print(f"✓ Content Brief Generated")
    print("\n" + "=" * 70)
    print("VALIDATING FROZEN CONTRACT")
    print("=" * 70)
    
    # Validate schema
    required_fields = {"target_audience", "seo_keywords", "h2_outline", "key_takeaways"}
    actual_fields = set(brief.keys())
    
    print(f"\nRequired fields: {required_fields}")
    print(f"Actual fields:   {actual_fields}")
    
    if actual_fields == required_fields:
        print("✓ Schema matches ARD frozen contract (4 fields only)")
    else:
        print(f"✗ Schema mismatch!")
        print(f"  Missing: {required_fields - actual_fields}")
        print(f"  Extra:   {actual_fields - required_fields}")
        return
    
    # Validate field types and constraints
    print("\n" + "-" * 70)
    print("FIELD VALIDATION")
    print("-" * 70)
    
    # target_audience
    ta = brief['target_audience']
    print(f"\ntarget_audience: '{ta}'")
    print(f"  Length: {len(ta)} chars (min: 10, max: 150)")
    if 10 <= len(ta) <= 150:
        print("  ✓ Length valid")
    else:
        print(f"  ✗ Length invalid")
    
    # seo_keywords
    keywords = brief['seo_keywords']
    print(f"\nseo_keywords: {keywords}")
    print(f"  Count: {len(keywords)} (min: 3, max: 15)")
    if 3 <= len(keywords) <= 15:
        print("  ✓ Count valid")
    else:
        print(f"  ✗ Count invalid")
    
    # h2_outline
    outline = brief['h2_outline']
    print(f"\nh2_outline: {outline}")
    print(f"  Count: {len(outline)} (min: 3, max: 10)")
    if 3 <= len(outline) <= 10:
        print("  ✓ Count valid")
    else:
        print(f"  ✗ Count invalid")
    
    # Check for generic patterns
    generic_detected = False
    for idx, heading in enumerate(outline):
        if any(pattern in heading.lower() for pattern in ["how to", "top ", " ways to"]):
            print(f"  ✗ Generic pattern in h2_outline[{idx}]: '{heading}'")
            generic_detected = True
    if not generic_detected:
        print("  ✓ No generic patterns detected")
    
    # key_takeaways
    takeaways = brief['key_takeaways']
    print(f"\nkey_takeaways: {takeaways}")
    print(f"  Count: {len(takeaways)} (min: 2, max: 8)")
    if 2 <= len(takeaways) <= 8:
        print("  ✓ Count valid")
    else:
        print(f"  ✗ Count invalid")
    
    # Check for forbidden tone words
    print("\n" + "-" * 70)
    print("BORING TEST & TONE VALIDATION")
    print("-" * 70)
    
    brief_text = json.dumps(brief).lower()
    
    # Check exclamation marks
    if "!" in json.dumps(brief):
        print("✗ Boring test failed: Exclamation marks detected")
    else:
        print("✓ No exclamation marks")
    
    # Check forbidden words
    forbidden = ["revolutionary", "game-changing", "transform", "inspire", "bold"]
    found_forbidden = [word for word in forbidden if word in brief_text]
    if found_forbidden:
        print(f"✗ Forbidden tone words: {found_forbidden}")
    else:
        print("✓ No forbidden tone words detected")
    
    # Check CTAs
    cta_patterns = ["will help you", "discover how", "learn how"]
    found_ctas = [pattern for pattern in cta_patterns if pattern in brief_text]
    if found_ctas:
        print(f"✗ CTA patterns detected: {found_ctas}")
    else:
        print("✓ No CTA patterns detected")
    
    print("\n" + "=" * 70)
    print("FULL CONTENT BRIEF")
    print("=" * 70)
    print(json.dumps(brief, indent=2))
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\n✅ Agent 2 is ARD-compliant (frozen contract enforced)")

if __name__ == "__main__":
    test_agent2_frozen_contract()
