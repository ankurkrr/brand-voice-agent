# Database Design

The system relies on MySQL for state persistence and relational mapping, supplemented by ChromaDB for semantic vector search.

## 1. MySQL Relational Schema

```mermaid
erDiagram
    brands ||--o{ voice_profiles : has
    brands ||--o{ content_briefs : has
    brands ||--o{ generated_content : has
    
    brands {
        string id PK "Passed from Platform org_id"
        string name
        datetime created_at
    }
    
    voice_profiles {
        string id PK
        string brand_id FK
        string version "Enum: v1, v2"
        json tone_descriptors
        json rules
        json dimensional_scores "Nullable for v1"
        string chroma_collection_id "Reference to vector DB"
    }
    
    content_briefs {
        string id PK
        string brand_id FK
        string topic
        json seo_keywords
        json outline
    }
    
    generated_content {
        string id PK
        string brand_id FK
        string profile_id FK
        string brief_id FK
        string platform "Enum: blog, twitter, linkedin"
        text content
    }
```

## 2. ChromaDB (Vector Store)

To capture the *implicit* stylistic nuances of a brand (which are hard to define in rigid rules), Agent 1 creates a ChromaDB collection for each `brand_id`.
- **Embedding Model:** `text-embedding-004` (Google)
- **Process:** Brand PDFs/URLs are chunked into 500-token segments and embedded.
- **Usage:** During Agent 3's execution, the LLM queries ChromaDB for the 3 most stylistically relevant chunks to use as few-shot examples in its system prompt.
