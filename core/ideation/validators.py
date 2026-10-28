"""
Content Brief Validators - Agent 2 Boundary Enforcement

Enforces strict separation between Agent 2 (strategy) and Agent 3 (style).
Scans Agent 2 output for tone/voice contamination and rejects anything publishable.

Validation Layers:
1. Forbidden Tone Words: Blocks marketing fluff ("revolutionary", "game-changing")
2. Boring Test: Rejects exclamation marks and emotional language
3. CTA Pattern Detection: Blocks persuasive phrases ("discover how", "learn why")
4. Noun Phrase Validation: Ensures concise labels, not sentences

Philosophy: "If it sounds like marketing copy, it fails."
Agent 2 must be analytically boring - pure strategy, no style.

Key Functions:
- validate_content_brief(): Main validation pipeline (hard-fail on violations)
- boring_test(): Emotional language detector
- check_cta_patterns(): Blocks calls-to-action

Purpose: Prevent tone leakage from Agent 2 → Agent 3
"""
from typing import List, Dict, Any
import json
import re

# Expanded forbidden tone words (50+ words)
FORBIDDEN_TONE_WORDS = {
    # Marketing fluff
    "revolutionary", "game-changing", "cutting-edge", "innovative",
    "groundbreaking", "world-class", "best-in-class", "industry-leading",
    "next-generation", "state-of-the-art", "leading-edge",
    
    # Persuasive verbs
    "transform", "unlock", "unleash", "skyrocket", "supercharge",
    "revolutionize", "disrupt", "empower", "elevate", "maximize",
    "accelerate", "amplify",  # Removed "optimize" - it's analytical, not persuasive
    
    # Tone adjectives
    "bold", "inspiring", "exciting", "dynamic", "vibrant",
    "passionate", "compelling", "engaging", "powerful", 
    "impactful", "stunning", "remarkable", "extraordinary",
    
    # Copy language
    "discover", "imagine", "envision", "achieve", "master",
    "breakthrough", "delve", "tapestry", "leverage"
}

# CTA and persuasive patterns
FORBIDDEN_COPY_PATTERNS = [
    r"will (help|enable|allow|empower) you",
    r"discover (how|why|the|what)",
    r"learn (how|why|what|the secrets)",
    r"ready to",
    r"imagine if",
    r"are you (ready|prepared|looking)",
    r"don't miss",
    r"act now",
    r"limited time"
]

def validate_content_brief(brief: Dict[str, Any]) -> None:
    """
    PHASE 2.2: Hard validation for strategy-only output.
    Agent-2 must be boring, analytical, and void of marketing language.
    """
    # 1. Scan for forbidden tone words
    _scan_recursive(brief)
    
    # 2. Boring Test
    boring_test(brief)
    
    # 3. CTA Pattern Detection
    check_cta_patterns(brief)
    
    # 4. Noun Phrase Validation
    validate_noun_phrases(brief)


def boring_test(brief: Dict[str, Any]) -> None:
    """
    If publishable as marketing copy → FAIL.
    Agent-2 must be analytically boring.
    """
    text = json.dumps(brief)
    
    # No exclamation marks
    if "!" in text:
        raise ValueError("Boring test failed: Exclamation marks detected. Agent-2 must be analytical.")
    
    # No emotional language
    emotional_words = [
        "amazing", "incredible", "excited", "thrilled", "delighted",
        "fantastic", "awesome", "wonderful", "terrific"
    ]
    text_lower = text.lower()
    for word in emotional_words:
        if word in text_lower:
            raise ValueError(f"Boring test failed: Emotional word '{word}' detected. Agent-2 must be analytical.")


def check_cta_patterns(brief: Dict[str, Any]) -> None:
    """
    Block call-to-action patterns.
    Agent-2 is strategy, not persuasion.
    """
    text = json.dumps(brief)
    
    for pattern in FORBIDDEN_COPY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(f"CTA pattern detected: {pattern}. Agent-2 must not contain calls-to-action.")


def validate_noun_phrases(brief: Dict[str, Any]) -> None:
    """
    Ensure target_audience and h2_outline are noun phrases, not sentences.
    """
    # Check target_audience
    if "target_audience" in brief:
        text = brief["target_audience"]
        forbidden_verbs = ["will", "can", "should", "must", "could", "would", "are", "is"]
        words = text.lower().split()
        for verb in forbidden_verbs:
            if verb in words:
                raise ValueError(
                    f"target_audience must be noun phrase, found verb '{verb}': '{text}'"
                )
    
    # Check h2_outline items
    if "h2_outline" in brief:
        for idx, heading in enumerate(brief["h2_outline"]):
            # Block "How to", "Top N", "X ways to"
            generic_patterns = [
                r"^how to",
                r"^top \d+",
                r"\d+ ways to",
                r"^everything you need"
            ]
            for pattern in generic_patterns:
                if re.search(pattern, heading, re.IGNORECASE):
                    raise ValueError(
                        f"h2_outline[{idx}] uses generic pattern '{pattern}': '{heading}'. Be specific."
                    )


def _scan_recursive(data: Any, path: str = "") -> None:
    """Recursively scan for forbidden tone words"""
    if isinstance(data, dict):
        for k, v in data.items():
            _scan_recursive(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _scan_recursive(item, f"{path}[{i}]")
    elif isinstance(data, str):
        # Check forbidden tone words
        words = set(data.lower().split())
        intersection = words.intersection(FORBIDDEN_TONE_WORDS)
        if intersection:
            raise ValueError(
                f"Validation Failed: Forbidden tone words {intersection} at '{path}'. "
                f"Agent-2 must be analytical, not persuasive."
            )
        
        # Check for excessive length (paragraphs)
        if len(data.split()) > 50:
            if "audience" not in path and "takeaway" not in path:
                raise ValueError(
                    f"Validation Failed: Text at '{path}' is too long ({len(data.split())} words). "
                    f"Agent-2 must produce brief points, not paragraphs."
                )
