import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

candidates = [
    "models/embedding-001",
    "embedding-001",
    "models/text-embedding-004",
    "gemini-embedding-001"
]

print("Testing embedding models...")

for model in candidates:
    print(f"\nTesting model: {model}")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
        # Try to embed something
        res = embeddings.embed_query("Hello world")
        print(f"SUCCESS: {model} works! Vector length: {len(res)}")
        break # Stop on first success
    except Exception as e:
        print(f"FAILED: {model} - Error: {e}")
