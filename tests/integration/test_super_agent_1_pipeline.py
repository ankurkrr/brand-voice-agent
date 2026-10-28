# tests/integration/test_super_agent_1_pipeline.py
import tempfile
import pytest
from lib.loaders.file import load_pdf
from core.voice.profile_composer import compose_voice_profile
from langchain_core.documents import Document

# helper to write a minimal valid PDF (MuPDF accepts this)
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.mark.asyncio
async def test_super_agent_1_pipeline(tmp_path):
    # 1) create minimal PDF file that MuPDF will open
    tmp = tmp_path / "brand_fake.pdf"
    tmp.write_bytes(MINIMAL_PDF)

    # 2) load PDF
    docs = load_pdf(str(tmp))
    assert isinstance(docs, list) and len(docs) >= 0

    # 3) simulate compose call (use small stubs where required)
    rules_input = "\n\n".join([d.page_content for d in docs if d.page_content]) or "Do: Be clear."
    # call compose_voice_profile with dummy brand and collection name
    profile = await compose_voice_profile(
        brand_id="test-brand-000",
        source_docs=docs,
        source_text_for_rules=rules_input,
        collection_name="brand_test"
    )
    assert "profile_id" in profile
