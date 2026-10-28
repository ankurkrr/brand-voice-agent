# Brand Voice Agent - Architecture Diagram

## System Overview

```mermaid
graph TB
    subgraph Frontend["Frontend Layer (Static HTML/JS)"]
        UI1["/templates/index.html<br/>Agent 1: Ingest UI"]
        UI2["/templates/ideation.html<br/>Agent 2: Ideation UI"]
        UI3["/templates/execution.html<br/>Agent 3: Execution UI"]
    end

    subgraph API["API Layer (FastAPI - Port 8082)"]
        R1["/ingest<br/>IngestRouter"]
        R2["/ideation/ideate<br/>IdeationRouter"]
        R3["/execute<br/>ExecutionRouter"]
        R4["/brands<br/>BrandRouter"]
        R5["/profiles<br/>ProfileRouter"]
    end

    subgraph Agents["Agent Layer (Core Business Logic)"]
        A1["Agent 1: Brand Voice Profiler<br/>(The Style Police)"]
        A2["Agent 2: Content Strategist<br/>(The Researcher)"]
        A3["Agent 3: Multi-Channel Executor<br/>(The Writer)"]
    end

    subgraph Support["Support Modules"]
        V1["Voice Module<br/>rule_extractor<br/>profile_composer<br/>example_selector"]
        I1["Ideation Module<br/>brief_builder<br/>normalizer<br/>web_research (Tavily)"]
        E1["Execution Module<br/>compliance_detector<br/>factual_spine<br/>platform_validator"]
    end

    subgraph Storage["Storage Layer"]
        DB[(MySQL Database<br/>voice_meta)]
        VDB[("ChromaDB<br/>(Vector Store)")]
    end

    subgraph External["External Services"]
        LLM["Google Gemini 2.5 Flash<br/>(LLM)"]
        WEB["Tavily API<br/>(Web Research)"]
    end

    %% Frontend to API
    UI1 -->|POST /ingest| R1
    UI2 -->|POST /ideation/ideate| R2
    UI3 -->|POST /execute| R3

    %% API to Agents
    R1 --> A1
    R2 --> A2
    R3 --> A3

    %% Agents to Support Modules
    A1 --> V1
    A2 --> I1
    A3 --> E1

    %% Support to External Services
    V1 --> LLM
    I1 --> LLM
    I1 --> WEB
    E1 --> LLM

    %% Storage Connections
    A1 -->|Save Voice Profile| DB
    A1 -->|Store Text Chunks| VDB
    A2 -->|Save Content Brief| DB
    A3 -->|Save Generated Content| DB
    A3 -->|Read Profile + Brief| DB
    V1 -->|Fetch Examples| VDB

    style A1 fill:#e1f5ff
    style A2 fill:#fff4e1
    style A3 fill:#e8f5e9
    style DB fill:#f3e5f5
    style VDB fill:#fff3e0
    style LLM fill:#ffebee
    style WEB fill:#e0f2f1
```

---

## Agent Pipeline Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Frontend UI
    participant API as FastAPI Router
    participant A1 as Agent 1<br/>(Voice)
    participant A2 as Agent 2<br/>(Ideation)
    participant A3 as Agent 3<br/>(Execution)
    participant DB as MySQL Database
    participant VDB as ChromaDB
    participant LLM as Gemini LLM
    participant WEB as Tavily API

    rect rgb(225, 245, 255)
    Note over User,VDB: PHASE 1: Brand Voice Extraction
    User->>UI: Upload Brand PDF
    UI->>API: POST /ingest
    API->>A1: run_agent1(docs, text)
    A1->>VDB: Store text chunks
    A1->>LLM: Extract rules (tone, dos, donts)
    LLM-->>A1: Rules JSON
    A1->>VDB: Fetch best examples
    VDB-->>A1: Top 3 examples
    A1->>DB: Save Voice Profile
    DB-->>A1: profile_id
    A1-->>API: Golden Record
    API-->>UI: profile_id, tone summary
    end

    rect rgb(255, 244, 225)
    Note over User,WEB: PHASE 2: Content Strategy Generation
    User->>UI: Enter Topic + Brand
    UI->>API: POST /ideation/ideate
    API->>A2: run_agent2(brand_id, topic)
    A2->>DB: Verify brand exists
    A2->>WEB: gather_web_signals(topic)
    WEB-->>A2: Search results (titles, snippets)
    A2->>LLM: Build content brief
    LLM-->>A2: Brief JSON
    A2->>A2: Normalize & Validate<br/>(strip tone language)
    A2->>DB: Save Content Brief
    DB-->>A2: brief_id
    A2-->>API: Strategic Brief
    API-->>UI: brief_id, audience, key messages
    end

    rect rgb(232, 245, 233)
    Note over User,LLM: PHASE 3: Multi-Platform Content Generation
    User->>UI: Select Brand + Platforms
    UI->>API: POST /execute (brand_id, platforms)
    API->>DB: Fetch Voice Profile
    API->>DB: Fetch Content Brief
    API->>A3: run_agent3(profile, brief, platforms)
    A3->>LLM: Generate content (with examples)
    LLM-->>A3: Platform content JSON
    A3->>A3: Compliance Check<br/>(forbidden phrases)
    alt Violations Found
        A3->>LLM: Rewrite (max 2 retries)
        LLM-->>A3: Corrected content
    end
    A3->>A3: Platform Validation<br/>(char limits, structure)
    A3->>A3: Factual Spine Check<br/>(all key messages present)
    A3->>DB: Save Generated Content
    A3-->>API: Blog, LinkedIn, Twitter, Email
    API-->>UI: Platform-native content
    end
```

---

## Database Schema

```mermaid
erDiagram
    brands ||--o{ voice_profiles : has
    brands ||--o{ content_briefs : has
    brands ||--o{ generated_content : has
    voice_profiles ||--o{ content_briefs : references
    voice_profiles ||--o{ generated_content : references
    content_briefs ||--o{ generated_content : references

    brands {
        char(36) id PK
        char(36) brand_id UK
        varchar(255) name
        timestamp created_at
    }

    voice_profiles {
        char(36) id PK
        char(36) profile_id UK
        char(36) brand_id FK
        int version
        varchar(50) status
        json profile_data
        timestamp created_at
    }

    content_briefs {
        char(36) id PK
        char(36) brand_id FK
        char(36) voice_profile_id FK
        varchar(255) topic
        json content_brief_json
        timestamp created_at
    }

    generated_content {
        char(36) id PK
        char(36) brand_id FK
        char(36) voice_profile_id FK
        char(36) content_brief_id FK
        json output_json
        json metadata
        timestamp created_at
    }
```

---

## Component Interaction Map

```mermaid
graph LR
    subgraph "Agent 1: Voice Profiler"
        A1[agent1.py]
        A1 --> RE[rule_extractor]
        A1 --> SA[style_analysis]
        A1 --> PC[profile_composer]
        PC --> ES[example_selector]
        PC --> RN[rule_normalizer]
    end

    subgraph "Agent 2: Strategist"
        A2[agent2.py]
        A2 --> BB[brief_builder]
        BB --> WR[web_research<br/>Tavily]
        A2 --> NM[normalizer]
        A2 --> VL[validators<br/>Boundary Check]
    end

    subgraph "Agent 3: Executor"
        A3[agent3.py]
        A3 --> CD[compliance_detector<br/>Voice Check]
        A3 --> FS[factual_spine<br/>Key Messages]
        A3 --> PV[platform_validator<br/>Char Limits]
        A3 --> SV[strict_validator<br/>Input Check]
    end

    style A1 fill:#e1f5ff
    style A2 fill:#fff4e1
    style A3 fill:#e8f5e9
```

---

## Data Flow: Golden Record Creation

```mermaid
flowchart TD
    Start([User Uploads PDF]) --> Load[Load Document<br/>PDF/DOCX/URL Loader]
    Load --> Chunk[Chunk Text<br/>500 tokens/chunk]
    Chunk --> Store[Store in ChromaDB<br/>collection: brand_123]
    
    Store --> Extract[LLM: Extract Rules<br/>gemini-2.5-flash]
    Extract --> Rules{Rules Valid?}
    
    Rules -->|Yes| Metrics[Calculate Style Metrics<br/>avg sentence length, etc.]
    Rules -->|No| Error1[Return Error]
    
    Metrics --> Examples[Fetch Best Examples<br/>Centroid similarity + quality]
    Examples --> Normalize[Normalize Vocabulary<br/>Filter ideology terms]
    
    Normalize --> Assemble[Assemble Golden Record<br/>tone + rules + examples]
    Assemble --> Save[(Save to voice_profiles<br/>MySQL)]
    Save --> End([Return profile_id])

    style Start fill:#e8f5e9
    style End fill:#e8f5e9
    style Error1 fill:#ffebee
```

---

## Boundary Enforcement Architecture

```mermaid
graph TB
    subgraph User Input
        I1[Raw Content]
    end

    subgraph "Agent 1: Style Police"
        A1P[Process Content]
        A1P --> GR[Create Golden Record:<br/>tone, dos, donts,<br/>forbidden phrases,<br/>examples]
        GR --> DB1[(voice_profiles)]
    end

    subgraph "Agent 2: Strategist"
        A2P[Process Topic]
        A2P --> BR[Create Brief:<br/>audience, key messages,<br/>SEO keywords, outline]
        BR --> V2{Validator:<br/>Tone Leakage?}
        V2 -->|Pass| DB2[(content_briefs)]
        V2 -->|Fail| ERR2[REJECT:<br/>No marketing copy allowed]
    end

    subgraph "Agent 3: Executor"
        DB1 --> A3I[Fetch Voice Profile]
        DB2 --> A3I
        A3I --> A3P[Generate Content]
        A3P --> V3A{Compliance:<br/>Forbidden phrases?}
        V3A -->|Violations| RW[Rewrite Loop<br/>Max 2 attempts]
        RW --> A3P
        V3A -->|Pass| V3B{Platform:<br/>Char limits OK?}
        V3B -->|Fail| ERR3[REJECT:<br/>Rewrite content]
        V3B -->|Pass| V3C{Factual Spine:<br/>All key messages?}
        V3C -->|Fail| ERR4[REJECT:<br/>Missing messages]
        V3C -->|Pass| DB3[(generated_content)]
    end

    I1 --> A1P
    
    style A1P fill:#e1f5ff
    style A2P fill:#fff4e1
    style A3P fill:#e8f5e9
    style ERR2 fill:#ffebee
    style ERR3 fill:#ffebee
    style ERR4 fill:#ffebee
```

---

## Technology Stack

```mermaid
mindmap
  root((Brand Voice Agent))
    Backend
      FastAPI
      Python 3.10+
      Uvicorn
    Database
      MySQL
        brands
        voice_profiles
        content_briefs
        generated_content
      ChromaDB
        Vector embeddings
        Text chunks
    AI/ML
      Google Gemini 2.5 Flash
      LangChain
      Text embeddings
    External APIs
      Tavily
        Web research
        Competitor analysis
    Frontend
      HTML/JS
      Static templates
      Fetch API
```
