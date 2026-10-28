# lib/text/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List

def chunk_documents(docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = [d.page_content for d in docs]
    chunks = splitter.split_documents([Document(page_content=t) for t in texts])
    # Each chunk is a Document
    return chunks
