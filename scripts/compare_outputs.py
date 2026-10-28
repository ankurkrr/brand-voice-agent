import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from core.agents.v1.agent1_voice import run_agent1
from core.models.document import Document

async def generate_comparison():
    # Mock Data matching ARD V1 Scope
    mock_rules = {
        "tone": {"primary": "Professional", "secondary": ["Authoritative", "Direct"], "description": "Professional and direct."},
        "dos": ["Use active voice", "Keep sentences under 20 words"],
        "donts": ["Use emojis", "Use slang", "Be passive"],
        "forbidden_phrases": ["synergy", "deep dive"],
        "preferred_vocabulary": ["execute", "deliver"],
        "style_metrics": {"avg_sentence_length": 15, "readability_grade": 8}
    }
    
    # Mock Data matching ARD V2 Scope
    mock_scores = {
        "Humor": 0.1,
        "Empathy": 0.4,
        "Authority": 0.9,
        "Formality": 0.8,
        "Urgency": 0.6
    }
    
    # Mock inputs
    docs = [Document(page_content="Sample content", metadata={})]
    text = "Sample content"
    collection = "brand_test"
    
    # Apply Mocks
    with patch("core.agents.v1.agent1_voice.extract_rules_from_text", new_callable=AsyncMock) as mock_extract, \
         patch("core.agents.v1.agent1_voice.DimensionalScorer") as MockScorerClass:
         
        mock_extract.return_value = mock_rules
        
        mock_scorer_instance = MockScorerClass.return_value
        mock_scorer_instance.score_dimensions = AsyncMock(return_value=mock_scores)
        
        # Run Agent 1 (which encompasses both V1 and V2 logic now)
        result = await run_agent1(
            source_docs=docs,
            source_text_for_rules=text,
            collection_name=collection,
            persona_name="CEO_Persona",
            brand_id="b_123"
        )
        
        golden_record = result["raw_json"]
        
        # Construct V1 Output View (Phase 1: Style Mimic)
        v1_output = {
            "tone": golden_record["explicit_rules"]["tone"],
            "dos": golden_record["explicit_rules"]["dos"],
            "donts": golden_record["explicit_rules"]["donts"],
            "examples_count": golden_record["examples_meta"]["count"]
        }
        
        # Construct V2 Output View (Phase 2: Multi-Persona Architect)
        v2_output = {
            "persona_id": golden_record["persona_id"],
            "persona_name": golden_record["persona_name"],
            "parent_persona_id": golden_record["parent_persona_id"],
            "dimensional_scores": golden_record["dimensional_scores"],
            "version": 2
        }
        
        # Print Side-by-Side
        print("\n" + "="*80)
        print(f"{'V1 OUTPUT (Phase 1)':<40} | {'V2 OUTPUT (Phase 2)':<40}")
        print("="*80)
        
        v1_json = json.dumps(v1_output, indent=2).splitlines()
        v2_json = json.dumps(v2_output, indent=2).splitlines()
        
        max_lines = max(len(v1_json), len(v2_json))
        for i in range(max_lines):
            left = v1_json[i] if i < len(v1_json) else ""
            right = v2_json[i] if i < len(v2_json) else ""
            print(f"{left:<40} | {right:<40}")
            
        print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(generate_comparison())
