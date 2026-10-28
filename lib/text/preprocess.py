# lib/text/preprocess.py
import re
from typing import List

def clean_text(text: str) -> str:
    # Basic cleaning: normalize whitespace, remove repeated newlines, strip headers/footers heuristics.
    t = text.replace("\r\n", "\n")
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    # Remove common PDF footers like 'Page 1 of 5' heuristically
    t = re.sub(r"Page\s+\d+\s+of\s+\d+", "", t, flags=re.IGNORECASE)
    return t.strip()

def join_documents(docs) -> str:
    # Concatenate LangChain Documents into a single text for analysis when needed
    return "\n\n".join([d.page_content for d in docs if d.page_content])
