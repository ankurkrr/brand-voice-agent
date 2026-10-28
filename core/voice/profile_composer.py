"""
Voice Profile Composer - Golden Record Assembly

Orchestrates the creation of a complete "Brand Voice Profile" by combining:
- Extracted rules (from rule_extractor)
- Style metrics (from style_analysis)
- Best examples (from example_selector)

Creates the "Golden Record" that Agent 3 uses for voice compliance enforcement.

Key Functions:
- compose_voice_profile(): Main orchestration, saves to DB
- build_system_prompt(): Formats rules into LLM-ready prompt

Called By: adapters/api/routers/ingest_router.py
Saves To: voice_profiles table (PostgreSQL/MySQL)
"""

import uuid
from langchain_core.documents import Document
from typing import List

from core.voice.rule_extractor import extract_rules_from_text
from core.voice.style_analysis import style_metrics_from_documents
from core.voice.example_selector import select_best_examples
from data.repos.voice_profiles import VoiceProfilesRepo



async def compose_voice_profile(
    brand_id: str,
    source_docs: List[Document],
    source_text_for_rules: str,
    collection_name: str,
    existing_profile_id: str = None
):
    raise RuntimeError(
        "compose_voice_profile() is V1-only and must not be called in V2 flows"
    )
    """
    Creates and stores a brand voice profile.
    """

    # Extract structured rules

    rules = await extract_rules_from_text(source_text_for_rules)

    # Extract writing style metrics
    style_metrics = style_metrics_from_documents(source_docs)

    # Get examples from vector DB
    examples = await select_best_examples(collection_name, top_k=3)

    # Build system prompt
    system_prompt = build_system_prompt(rules, style_metrics, examples)

    # Create profile JSON
    profile_data = {
        "collection_name": collection_name,
        "system_prompt": system_prompt,
        "tone": rules["tone"],
        "rules": {
            "dos": rules["dos"],
            "donts": rules["donts"],
            "forbidden_phrases": rules["forbidden_phrases"],
            "preferred_vocabulary": rules["preferred_vocabulary"],
        },
        "style_metrics": style_metrics,
        "example_snippets": examples,
        "embedding_meta": {"model": "models/embedding-001"},
        "stats": {"acceptance_rate": 0, "rewrite_count": 0},
    }


    # Save into Postgres
  
    if existing_profile_id:
        saved = await VoiceProfilesRepo.update_profile(
            profile_id=existing_profile_id,
            profile_data=profile_data
        )
    else:
        saved = await VoiceProfilesRepo.save_profile(
            brand_id=brand_id,
            profile_data=profile_data
        )

    return saved


# Helper: Build the system prompt for the model
def build_system_prompt(rules, style_metrics, examples):
    lines = []

    lines.append(
        f"You are the brand's copywriter.\n"
        f"Primary tone: {rules['tone'].get('primary', '')}\n"
        f"Secondary tones: {', '.join(rules['tone'].get('secondary', []))}"
    )

    lines.append("\nDOs:")
    for d in rules["dos"]:
        lines.append(f"- {d}")

    lines.append("\nDON'Ts:")
    for d in rules["donts"]:
        lines.append(f"- {d}")

    if rules["forbidden_phrases"]:
        lines.append(f"\nForbidden phrases: {', '.join(rules['forbidden_phrases'])}")

    lines.append(f"\nAverage sentence length: {style_metrics.get('avg_sentence_length')} words")

    lines.append("\nExample tone snippets:")
    for e in examples:
        lines.append(f"> {e['text'][:250]}")

    return "\n".join(lines)
