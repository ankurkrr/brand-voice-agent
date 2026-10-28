
from lib.utils.json_repair import safe_parse_json, repair_json
import json

def test_repair_logic():
    cases = [
        # Case 1: Missing comma in list
        ('["item1" "item2"]', ["item1", "item2"]),
        # Case 2: Trailing comma in object
        ('{"key": "value",}', {"key": "value"}),
        # Case 3: Trailing comma in list
        ('["item1",]', ["item1"]),
        # Case 5: Standard JSON
        ('{"a": 1}', {"a": 1}),
        # Case 6: Nested missing comma
        ('{"list": ["a" "b"]}', {"list": ["a", "b"]}),
         # Case 7: Markdown block
        ('```json\n{"key": "value"}\n```', {"key": "value"}),
        # Case 8: Messy text with JSON
        ('Here is some text {"key": "value"} and more text', {"key": "value"}),
    ]

    print("Running JSON Repair Tests...")
    failures = 0
    for input_str, expected in cases:
        try:
            result = safe_parse_json(input_str)
            if result != expected:
                print(f"[FAIL] Input: {input_str}\n  Got: {result}\n  Exp: {expected}")
                failures += 1
            else:
                print(f"[PASS] {input_str[:30]}...")
        except Exception as e:
            print(f"[ERROR] Input: {input_str}\n  Exception: {e}")
            failures += 1
    
    if failures == 0:
        print("\nALL TESTS PASSED")
    else:
        print(f"\n{failures} TESTS FAILED")

if __name__ == "__main__":
    test_repair_logic()
