# tests/e2e/test_ingest_api.py

import asyncio
from fastapi.testclient import TestClient
from api.server import app
from data.repos.brands import BrandsRepo
from anyio import from_thread


client = TestClient(app)

def test_ingest_api_txt():
    # 1) Create brand in test database
    brand = from_thread.run(BrandsRepo.create_brand("Test Brand"))
    brand_id = str(brand["brand_id"])

    # 2) Upload text file
    content = b"Do: Use active voice.\nDon't: Use emojis.\nWe help customers clearly."

    response = client.post(
        "/ingest/upload",
        data={"brand_id": brand_id},
        files={"file": ("sample.txt", content, "text/plain")}
    )

    assert response.status_code == 200, response.text