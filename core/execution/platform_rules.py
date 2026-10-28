"""
Platform Rules for Agent 3
Hardcoded, authoritative constraints for each platform
"""
from typing import Dict, Any


import yaml
import os

RULES_DIR = os.path.join(os.path.dirname(__file__), 'rules')

def _load_rules():
    """Load rules from YAML files in rules directory."""
    rules = {}
    for filename in os.listdir(RULES_DIR):
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            platform = os.path.splitext(filename)[0]
            with open(os.path.join(RULES_DIR, filename), 'r') as f:
                rules[platform] = yaml.safe_load(f)
    print(f"[PlatformRules] Loaded rules for: {list(rules.keys())}")
    return rules

# Load rules on module import (or lazy load)
PLATFORM_RULES: Dict[str, Dict[str, Any]] = _load_rules()


UNIVERSAL_CONSTRAINTS = {
    "no_contradictions": "All platforms must communicate the same core facts",
    "brand_voice_priority": "Brand voice rules override platform conventions if they conflict",
    "no_verbatim_reuse": "Never copy-paste text across platforms",
    "fact_preservation": "Never remove key messages to fit platform limits - rewrite instead"
}


def get_platform_rules(platform: str) -> Dict[str, Any]:
    """
    Get rules for a specific platform
    
    Args:
        platform: One of 'blog', 'linkedin', 'twitter', 'email'
        
    Returns:
        Dictionary of platform rules
        
    Raises:
        ValueError: If platform is not recognized
    """
    if platform not in PLATFORM_RULES:
        raise ValueError(f"Unknown platform: {platform}. Must be one of {list(PLATFORM_RULES.keys())}")
    
    return PLATFORM_RULES[platform]


def validate_platform_list(platforms: list) -> bool:
    """
    Validate that all platforms in list are recognized
    
    Args:
        platforms: List of platform names
        
    Returns:
        True if all valid, raises ValueError otherwise
    """
    invalid = [p for p in platforms if p not in PLATFORM_RULES]
    if invalid:
        raise ValueError(f"Invalid platforms: {invalid}. Must be from {list(PLATFORM_RULES.keys())}")
    return True
