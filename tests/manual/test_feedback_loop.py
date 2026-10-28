# Test script for Agent 1 Feedback Loop
import requests
import json

BASE_URL = "http://localhost:8082"

def test_feedback_endpoint():
    """Test the feedback endpoint implementation"""
    
    print("=" * 60)
    print("TESTING AGENT 1 FEEDBACK LOOP")
    print("=" * 60)
    
    # Step 1: Create a test brand and profile
    print("\n1. Creating test brand...")
    response = requests.post(f"{BASE_URL}/brands/create", json={"name": "TestBrand"})
    brand = response.json()
    print(f"✓ Brand created: {brand['brand_id']}")
    
    # Step 2: Ingest content to create voice profile
    print("\n2. Creating voice profile...")
    response = requests.post(
        f"{BASE_URL}/ingest",
        json={
            "brand_name": "TestBrand",
            "input_type": "text",
            "input_value": "We are professional. Use active voice. Never use jargon."
        }
    )
    ingest_result = response.json()
    brand_id = ingest_result['brand_id']
    print(f"✓ Voice profile created for brand: {brand_id}")
    
    # Step 3: Get profile_id (assuming it's linked to brand)
    # For now, we'll use a mock profile_id - in production, fetch from GET /profiles/{brand_id}
    profile_id = brand_id  # Simplified for test
    
    # Step 4: Test ACCEPT feedback
    print("\n3. Testing ACCEPT feedback...")
    response = requests.post(
        f"{BASE_URL}/profiles/{profile_id}/feedback",
        json={"action": "accept"}
    )
    if response.status_code == 200:
        feedback = response.json()
        print(f"✓ Accept recorded:")
        print(f"  - Acceptance rate: {feedback['acceptance_rate']*100}%")
        print(f"  - Rewrite count: {feedback['rewrite_count']}")
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
    
    # Step 5: Test REJECT feedback
    print("\n4. Testing REJECT feedback...")
    response = requests.post(
        f"{BASE_URL}/profiles/{profile_id}/feedback",
        json={"action": "reject"}
    )
    if response.status_code == 200:
        feedback = response.json()
        print(f"✓ Reject recorded:")
        print(f"  - Acceptance rate: {feedback['acceptance_rate']*100}%")
    else:
        print(f"✗ Failed: {response.status_code}")
    
    # Step 6: Test REWRITE feedback
    print("\n5. Testing REWRITE feedback...")
    response = requests.post(
        f"{BASE_URL}/profiles/{profile_id}/feedback",
        json={"action": "rewrite"}
    )
    if response.status_code == 200:
        feedback = response.json()
        print(f"✓ Rewrite recorded:")
        print(f"  - Acceptance rate: {feedback['acceptance_rate']*100}%")
        print(f"  - Rewrite count: {feedback['rewrite_count']}")
    else:
        print(f"✗ Failed: {response.status_code}")
    
    # Step 7: Get current stats
    print("\n6. Fetching current stats...")
    response = requests.get(f"{BASE_URL}/profiles/{profile_id}/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"✓ Final stats:")
        print(f"  - Total events: {stats['total_feedback_events']}")
        print(f"  - Acceptance rate: {stats['acceptance_rate']*100}%")
        print(f"  - Rewrite count: {stats['rewrite_count']}")
    else:
        print(f"✗ Failed: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_feedback_endpoint()
