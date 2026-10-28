
import json
import re

def extract_json_logic(content):
    # Validated: Extract JSON object more robustly
    content = content.strip()
    
    # 1. Try direct parse
    try:
        obj = json.loads(content)
        return "Direct Parse Success", obj
    except:
        pass

    # 2. Try handling Markdown code blocks (```json ... ```)
    match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            obj = json.loads(json_str)
            return "Markdown Parse Success", obj
        except:
            pass

    # 3. Fallback: Find first { and last }
    try:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            obj = json.loads(content[start:end+1])
            return "Fallback Parse Success", obj
    except Exception as e:
        return "Fail", str(e)

    return "Fail", "No valid JSON found"

def test_cases():
    cases = [
        ('{"key": "value"}', "Direct Parse Success"),
        ('```json\n{"key": "value"}\n```', "Markdown Parse Success"),
        ('Here is the json:\n```\n{"key": "value"}\n```', "Markdown Parse Success"),
        ('Some noisy text {"key": "value"} more noise', "Fallback Parse Success"),
        ('Invalid json { key: value }', "Fail"), # Invalid JSON syntax
    ]

    for input_str, expected in cases:
        result, _ = extract_json_logic(input_str)
        print(f"Input: {input_str[:20]}... -> Result: {result} (Expected: {expected})")
        if "Success" in expected and result != expected:
            print("  [FAILURE] Logic mismatch")

if __name__ == "__main__":
    test_cases()
