# core/storage/chroma_client.py

from chromadb import PersistentClient
import os
from dotenv import load_dotenv

load_dotenv()
CHROMA_DIR = os.getenv("CHROMA_DB_PATH", os.path.join(os.getcwd(), "chroma_data"))

# Singleton client
_client = None

def get_chroma_client():
    """
    Returns a persistent Chroma client instance.
    Uses the new PersistentClient API (Chroma v0.5+ compatible).
    """
    global _client

    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = PersistentClient(path=CHROMA_DIR)

    return _client

# Domain-Specific Collections (Semantic Isolation)
VOICE_COLLECTION_NAME = "voice_profiles"
IDEATION_COLLECTION_NAME = "ideation_sources"
EXAMPLES_COLLECTION_NAME = "few_shot_examples"

def get_voice_collection():
    """Get the isolated collection for Voice Profiles."""
    client = get_chroma_client()
    return client.get_or_create_collection(VOICE_COLLECTION_NAME)

def get_ideation_collection():
    """Get the isolated collection for Ideation Sources."""
    client = get_chroma_client()
    return client.get_or_create_collection(IDEATION_COLLECTION_NAME)

def get_examples_collection():
    """Get the isolated collection for Few-Shot Examples."""
    client = get_chroma_client()
    return client.get_or_create_collection(EXAMPLES_COLLECTION_NAME)
