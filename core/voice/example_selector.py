"""
Voice Example Selector - Best-Match Content Retrieval

Selects the most representative examples of brand writing from the vector store.
Uses centroid-based similarity + quality scoring to identify "golden examples".

Key Functions:
- select_best_examples(): Returns top-k examples closest to brand centroid
- cosine_similarity(): Vector distance calculation

Algorithm:
1. Fetch all embeddings from ChromaDB collection
2. Calculate centroid vector (mean of all embeddings)
3. Rank chunks by similarity to centroid  
4. Re-rank top candidates by quality score (sentence length, passive voice, etc.)
5. Return top-k highest quality examples

Called By: core/voice/profile_composer.py
Used In: Agent 3 prompt (shows examples of "how we write")
"""
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from core.storage.chroma_client import get_chroma_client
from core.storage.vector import get_embeddings_provider
from core.voice.style_analysis import avg_sentence_length, vocabulary_profile, detect_passive_voice


import numpy as np
from core.voice.style_analysis import score_text_quality

def cosine_similarity(v1, v2):
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return np.dot(v1, v2) / (norm_v1 * norm_v2)

async def select_best_examples(collection_name: str, top_k: int = 3):
    client = get_chroma_client()
    
    try:
        collection = client.get_collection(name=collection_name)
        # Fetch embeddings to calculate centroid
        results = collection.get(include=["documents", "metadatas", "embeddings"])
        
        if not results or not results.get("embeddings"):
            return []

        embeddings = np.array(results["embeddings"])
        documents = results["documents"]
        
        if len(embeddings) == 0:
            return []

        # Calculate Centroid (Mean Vector)
        centroid = np.mean(embeddings, axis=0)
        
        # Calculate similarity to centroid for each chunk
        candidates = []
        for idx, emb in enumerate(embeddings):
            sim = cosine_similarity(emb, centroid)
            candidates.append({
                "text": documents[idx],
                "sim_score": sim,
                "metadata": results["metadatas"][idx]
            })
            
        # 1. Filter by Similarity (Top 2 * k to get a pool of relevant candidates)
        candidates.sort(key=lambda x: x["sim_score"], reverse=True)
        pool = candidates[:top_k * 2] 

        # 2. Re-rank Pool by Quality Score
        for c in pool:
            c["quality_score"] = score_text_quality(c["text"])

        # Sort by quality descending
        pool.sort(key=lambda x: x["quality_score"], reverse=True)
        
        # Return top_k quality examples
        return pool[:top_k]

    except Exception as e:
        print(f"Error selecting examples: {e}")
        return []
