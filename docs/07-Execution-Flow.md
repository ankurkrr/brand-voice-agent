# Execution Flow

This sequence diagram illustrates the strict state machine flow orchestrated via the REST API, simulating an external platform (via MCP) executing the full Meta-Agent pipeline.

```mermaid
sequenceDiagram
    autonumber
    actor Platform as MCP Server (External)
    participant API as FastAPI Router
    participant Agent1 as Voice Profiler
    participant Agent2 as Strategist
    participant Agent3 as Executor
    participant DB as MySQL DB

    Platform->>API: POST /pipeline/start?brand_id=org_123
    API->>DB: Create Pipeline (State: IDLE)
    API-->>Platform: Returns pipeline_id
    
    Platform->>API: POST /pipeline/{id}/step/voice_profiling (URL)
    API->>DB: Update State: IN_PROGRESS
    API->>Agent1: Ingest URL & Extract Tone
    Agent1-->>API: Voice Profile JSON
    API->>DB: Save Profile (v2)
    API-->>Platform: Returns Profile JSON
    
    Platform->>API: POST /pipeline/{id}/approve/voice_profiling
    API->>DB: Mark Step 1 Approved
    
    Platform->>API: POST /pipeline/{id}/step/ideation ("AI Trends")
    API->>Agent2: Research Topic (Tavily)
    Agent2-->>API: Content Brief JSON
    API->>DB: Save Content Brief
    API-->>Platform: Returns Content Brief
    
    Platform->>API: POST /pipeline/{id}/approve/ideation
    API->>DB: Mark Step 2 Approved
    
    Platform->>API: POST /pipeline/{id}/step/execution
    API->>DB: Fetch Approved Profile & Brief
    API->>Agent3: Generate Copy (Blog, Twitter)
    Agent3-->>API: Platform-Native Output
    API->>DB: Update State: COMPLETED
    API-->>Platform: Returns Generated Content
```

## Critical Flow Constraints
- **Idempotency:** Agent 2 (Ideation) uses fingerprint-based deduplication. If called twice with the exact same topic and market, it returns the cached result to save API costs.
- **Blocking Protection:** Agent 3 (Execution) is **NOT** safe to retry automatically, as it incurs expensive LLM calls. The external platform must handle timeouts (which should be set to >= 45s).
