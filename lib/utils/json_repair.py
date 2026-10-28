# lib/utils/json_repair.py

import re
import json

def repair_json(json_str: str) -> str:
    """
    Attempts to repair common JSON syntax errors produced by LLMs.
    1. Fixes trailing commas.
    2. Fixes missing commas between array items (conservative approach).
    3. Handles extra text before/after JSON.
    """
    if not json_str:
        return "{}"

    # 1. Fix trailing commas before closing braces/brackets
    # Matches: , \s* } -> }
    json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

    # 2. Fix missing commas between array items (more conservative)
    # Only fix if we see: "string"\n    "string" pattern (likely array items on separate lines)
    # This avoids corrupting strings that contain quotes
    # Pattern: closing quote, newline (with optional whitespace), opening quote
    json_str = re.sub(r'"\s*\n\s*"', '",\n    "', json_str)
    
    # 3. Fix missing commas between object properties
    # Pattern: "value"\n    "key": -> "value",\n    "key":
    json_str = re.sub(r'"\s*\n\s*"([^"]+)":', '",\n    "\\1":', json_str)

    return json_str

def safe_parse_json(content: str):
    """
    Tries to parse JSON, applying multiple repair strategies if standard parse fails.
    """
    # 1. Try clean
    try:
        return json.loads(content)
    except:
        pass

    # 2. Extract block if present
    match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
    if match:
        content = match.group(1).strip()
        try:
            return json.loads(content)
        except:
            pass
    
    # 3. Find { ... } and work with that
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        content = content[start:end+1]
    
    # 4. Apply basic repair and try
    repaired = repair_json(content)
    try:
        return json.loads(repaired)
    except Exception as e:
        # 5. Try aggressive array comma fix
        # Sometimes LLMs miss commas in arrays - let's fix line by line
        aggressive = aggressive_array_fix(repaired)
        try:
            return json.loads(aggressive)
        except Exception as final_e:
            raise ValueError(f"JSON Parse Failed even after repair: {final_e}")

    raise ValueError("No valid JSON found")


def aggressive_array_fix(json_str: str) -> str:
    """
    Aggressively fixes missing commas in arrays by analyzing line by line.
    Looks for patterns like:
        "item"
        "item"  (missing comma between)
    """
    lines = json_str.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if this line ends with a string or closing bracket/brace
        ends_with_string = stripped.endswith('"') and not stripped.endswith('",')
        ends_with_bracket = stripped.endswith(']') and not stripped.endswith(',')
        ends_with_brace = stripped.endswith('}') and not stripped.endswith(',')
        
        # Look ahead to next non-empty line
        if i < len(lines) - 1:
            next_line = lines[i + 1].strip()
            
            # If current line ends with " and next starts with ", add comma
            if ends_with_string and next_line.startswith('"'):
                line = line.rstrip() + ','
            # If current line ends with } and next starts with ", add comma
            elif ends_with_brace and next_line.startswith('"'):
                line = line.rstrip() + ','
            # If current line ends with ] and next starts with ", add comma
            elif ends_with_bracket and next_line.startswith('"'):
                line = line.rstrip() + ','
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)
