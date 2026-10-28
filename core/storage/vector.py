# core/storage/vector.py
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import os
from dotenv import load_dotenv

def get_embeddings_provider():
    """
    Use Gemini Embeddings: models/embedding-001
    """
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",                   # Google’s embedding model
        google_api_key=os.getenv("GOOGLE_API_KEY")   
    )

def upsert_chunks_to_chroma(chunks: List[Document], collection_name: str):
    embeddings = get_embeddings_provider()

    from core.storage.chroma_client import get_chroma_client
    client = get_chroma_client()

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        client=client
    )

    return vector_store

def fetch_chunks_from_chroma(collection_name: str) -> List[Document]:
    """
    Retrieve all documents from a chroma collection.
    """
    from core.storage.chroma_client import get_chroma_client
    client = get_chroma_client()
    
    # Get collection
    collection = client.get_collection(name=collection_name)
    if not collection:
        return []
        
    # Get all items
    result = collection.get()
    
    # Convert back to Documents
    documents = []
    ids = result.get('ids', [])
    metadatas = result.get('metadatas', [])
    documents_content = result.get('documents', [])
    
    for i in range(len(ids)):
        raw_metadata = (
            metadatas[i]
            if i < len(metadatas) and isinstance(metadatas[i], dict)
            else {}
        )

        doc = Document(
            page_content=documents_content[i],
            metadata=raw_metadata
        )
        documents.append(doc)

    return documents
