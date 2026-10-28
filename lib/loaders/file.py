# lib/loaders/file.py
from typing import List
from langchain_community.document_loaders import UnstructuredPDFLoader, UnstructuredURLLoader, Docx2txtLoader
from langchain_community.document_loaders import PyMuPDFLoader, PyPDFLoader
from lib.text.preprocess import clean_text
import sys

# DEBUG ADAPTER: PyMuPDF Fallback for Python 3.14+
try:
    import fitz
    from langchain_community.document_loaders import PyMuPDFLoader
    PYMUPDF_AVAILABLE = True
    print(f"[LOADER] fitz (PyMuPDF) successfully imported.")
except ImportError as e:
    PYMUPDF_AVAILABLE = False
    print(f"[LOADER] PyMuPDF not found (likely Python 3.14 incompatibility). Error: {e}")
    try:
        from langchain_community.document_loaders import PyPDFLoader
        print("[LOADER] Falling back to PyPDFLoader.")
    except ImportError:
        PyPDFLoader = None
        print("[LOADER] PyPDFLoader also not found. PDF ingestion will fail.")

from langchain_core.documents import Document

def load_brand_source(input_type: str, input_value: str) -> List[Document]:
    if input_type == "pdf":
        return load_pdf(input_value)
    elif input_type == "url":
        return load_url(input_value)
    elif input_type == "text":
        # Wrap raw text into a Document
        clean = clean_text(input_value)
        return [Document(page_content=clean)]
    else:
        raise ValueError(f"Unsupported input type: {input_type}")

def load_pdf(path: str):
    if PYMUPDF_AVAILABLE:
        print("[LOADER] Using PyMuPDFLoader")
        loader = PyMuPDFLoader(path)
    elif PyPDFLoader:
         print("[LOADER] Using PyPDFLoader (Fallback)")
         loader = PyPDFLoader(path)
    else:
        raise ImportError("No PDF Loader available. PyMuPDF is incompatible with Python 3.14, and pypdf is not installed.")

    docs = loader.load()
    for d in docs:
        d.page_content = clean_text(d.page_content)
    return docs


from lib.loaders.scrapers.website_scraper import WebsiteScraper

def load_url(url: str):
    scraper = WebsiteScraper()
    result = scraper.scrape_website(url)
    
    # Create document from combined text
    content = result.get('combined_text', '')
    if not content:
        # Fallback empty doc if scraping fails completely
        return []
        
    # Metadata including scrape method and content type
    metadata = {
        "source": url,
        "method": result.get('method', 'unknown'),
        "is_javascript_site": result.get('is_javascript_site', False)
    }
    
    return [Document(page_content=content, metadata=metadata)]

def load_docx(path: str):
    loader = Docx2txtLoader(path)
    docs = loader.load()
    for d in docs:
        d.page_content = clean_text(d.page_content)
    return docs
