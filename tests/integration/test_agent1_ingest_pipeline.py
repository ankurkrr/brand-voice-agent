import pytest
from reportlab.pdfgen import canvas

from lib.loaders.file import load_pdf
from lib.text.chunker import chunk_documents
from lib.text.preprocess import join_documents
from core.voice.profile_composer import compose_voice_profile
from data.repos.brands import BrandsRepo


# ---------------------------------------------------------
# Helper: create a REAL PDF for testing (required by PyMuPDF)
# ---------------------------------------------------------
def create_fake_pdf(path: str, text: str):
    c = canvas.Canvas(path)
    c.drawString(50, 800, text)
    c.save()


@pytest.mark.asyncio
async def test_full_agent1_ingest_pipeline(tmp_path):
    """
    End-to-end integration test for SuperAgent-1:
    PDF → loaders → chunker → rules → style → examples → DB save
    """

    # 1) Create valid PDF
    pdf_path = tmp_path / "brand_test.pdf"
    create_fake_pdf(str(pdf_path), "This is a test brand guideline. DO: Stay clear. DON'T: Use jargon.")

    # 2) Create a brand (Agent-1 requires foreign key)
    brand = await BrandsRepo.create_brand("Test Brand")

    # 3) Load the PDF
    docs = load_pdf(str(pdf_path))
    assert len(docs) > 0

    # 4) Chunk
    chunks = chunk_documents(docs)
    assert len(chunks) > 0

    # 5) Join text
    raw_text = join_documents(docs)
    assert "DO:" in raw_text

    # 6) Run SuperAgent-1
    profile = await compose_voice_profile(
        brand_id=brand["brand_id"],
        source_docs=docs,
        source_text_for_rules=raw_text,
        collection_name=f"brand_{brand['brand_id']}"
    )

    # 7) Validate result
    assert "profile_id" in profile
    assert profile["brand_id"] == brand["brand_id"]
    assert "profile_data" in profile