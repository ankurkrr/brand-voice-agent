"""
Voice Rule Normalizer - Quality Control Layer

Post-processes LLM-extracted rules to remove ideology, corporate jargon, and ensure
the "Golden Record" contains only actionable style guidelines.

Key Functions:
- normalize_rules(): LLM-powered normalization using normalization_v2.md prompt
- filter_vocabulary(): Deterministic blocklist for ideology terms
- validate_vocabulary(): Hard-fail guard against slippage

Blocklist Includes: Corporate speak ("synergy"), ideological framing ("revolutionize"), 
policy terms ("diversity"), mission statements ("purpose-driven")

Called By: core/voice/profile_composer.py
Purpose: Ensures Golden Record purity (style-only, no strategy/values)
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from pathlib import Path
import json

class NormalizedRuleSchema(BaseModel):
    tone: dict = {"primary": "", "secondary": []}
    dos: list[str] = []
    donts: list[str] = []

PROMPT_TEMPLATE = Path("prompts/normalization_v2.md").read_text(encoding="utf-8")

async def normalize_rules(raw_rules: dict) -> dict:
    """
    Takes raw extracted rules and normalizes them using the "Golden Record" prompt.
    """
    
    # Prepare input JSON string
    input_json = json.dumps({
        "tone": raw_rules.get("tone"),
        "dos": raw_rules.get("dos"),
        "donts": raw_rules.get("donts")
    }, indent=2)

    prompt = PromptTemplate(
        input_variables=["INPUT_JSON"],
        template=PROMPT_TEMPLATE.replace("<<<INPUT_JSON>>>", "{INPUT_JSON}")
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0
    )

    chain = prompt | llm

    raw = await chain.ainvoke({"INPUT_JSON": input_json})

    # Use robust JSON parsing utility
    from lib.utils.json_repair import safe_parse_json
    
    obj = None
    try:
        obj = safe_parse_json(raw.content)
    except Exception as e:
        # LOGGING for debugging
        print(f"NORMALIZER FAILED TO PARSE JSON. Error: {e}")
        print(f"RAW CONTENT:\n{raw.content[:1000]}")
        
        # Fallback to raw input (safety net)
        return {
            "tone": raw_rules.get("tone"),
            "dos": raw_rules.get("dos", []),
            "donts": raw_rules.get("donts", [])
        }

    # Validate with Pydantic
    normalized = NormalizedRuleSchema(**obj).dict()
    
    return normalized


# HARDENING: Deterministic Filter for Vocabulary
IDEOLOGY_KEYWORDS = {
    # Corporate / HR / Policy
    "wellbeing", "employee", "hr", "policy", "compliance", "ethics", "hiring",
    "recruiting", "benefits", "compensation", "diversity", "equity", "inclusion",
    "allyship", "belonging", "pay equity", "safety", "sustainability",
    
    # Mission / Vision / Values
    "mission", "vision", "values", "purpose", "impact", "social impact",
    "community", "commitment", "future", "legacy", "manifesto",
    
    # Investment / Business
    "invests", "investment", "shareholder", "stakeholder", "growth",
    "revenue", "profit", "market share",
    
    # Specific Slogans / Ideological Framing
    "future of sport", "defies convention", "game changer", "revolutionary",
    "disruptive", "democratize", "empowerment"
}

def filter_vocabulary(vocab_list: list[str]) -> list[str]:
    """
    Deterministically filters out ideology, policy, and business terms
    from the preferred vocabulary list.
    """
    filtered = []
    
    for term in vocab_list:
        term_lower = term.lower().strip()
        
        # Check against blocklist
        is_ideology = False
        for keyword in IDEOLOGY_KEYWORDS:
            if keyword in term_lower:  # Substring match (strict)
                is_ideology = True
                break
        
        if not is_ideology:
            filtered.append(term)
            
    # Deduplicate while preserving order
    seen = set()
    unique_filtered = []
    for item in filtered:
        if item not in seen:
            unique_filtered.append(item)
            seen.add(item)
            
    return unique_filtered

def validate_vocabulary(vocab_list: list[str]):
    """
    Guardrail: Raises error if any ideology terms slip through.
    This runs AFTER filtering to ensure "Golden Record" purity.
    """
    for term in vocab_list:
        term_lower = term.lower().strip()
        for keyword in IDEOLOGY_KEYWORDS:
            if keyword in term_lower:
                 # HARD FAIL as per requirement
                 raise ValueError(f"Golden Record violation: ideology term '{term}' detected in preferred_vocabulary")
