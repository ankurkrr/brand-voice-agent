# Technical Design Document (TRD)

## 1. Database Schema (MySQL)

The system relies on a relational model to maintain strict associations between a Brand, its Voice Profile, and the resulting Content.

**Core Tables:**
- `brands`: Master registry (`id`, `name`, `org_id_mapping`).
- `voice_profiles`: Output of Agent 1. Stores JSON payloads containing tone descriptors, explicit rules, and dimensional scores.
- `content_briefs`: Output of Agent 2. Stores the researched strategy (keywords, audience).
- `generated_content`: Output of Agent 3. Stores the final copy, mapped by platform (Blog, Twitter, etc.).

## 2. The State Machine (`PipelineController`)

To support external integrations (like MCP servers wrapping this API), the execution is modeled as a state machine. This prevents race conditions where Agent 3 is called before Agent 1 finishes.

**Pipeline States:**
- `IDLE` ➔ `IN_PROGRESS` ➔ `COMPLETED` / `FAILED`

**Step States:**
- `PENDING` ➔ `RUNNING` ➔ `COMPLETED` / `FAILED` / `SKIPPED`

**Execution Contract:**
1. Platform calls `POST /pipeline/start` ➔ returns `pipeline_id`.
2. Platform calls `POST /pipeline/{id}/step/voice_profiling` (Agent 1 runs synchronously, returns when `COMPLETED`).
3. Platform calls `POST /pipeline/{id}/approve/voice_profiling` (Human in the loop approval).
4. Platform calls `POST /pipeline/{id}/step/ideation` (Agent 2 runs).

## 3. Vector Storage Integration (ChromaDB)

While explicit rules (e.g., "Never use the word 'utilize'") are stored in MySQL and passed in the system prompt, *implicit* stylistic nuances are harder to prompt for. 
We solve this using **Retrieval-Augmented Generation (RAG) for Style**:
1. When Agent 1 parses a brand's top-performing blog post, it chunks the text and embeds it into ChromaDB.
2. When Agent 3 generates a new blog post, it queries ChromaDB for the most stylistically relevant chunks from the original text.
3. These chunks are injected into Agent 3's prompt as **Few-Shot Examples**, drastically improving stylistic mimicry.

## 4. Null Safety & Versioning

Because AI outputs evolve, the API enforces strict versioning on Voice Profiles:
- `v1`: Legacy profiles. Purely text-based rules.
- `v2`: Enhanced profiles. Includes `dimensional_scores` (e.g., Formal vs. Casual: 8/10) intended for frontend Radar Charts.

**Technical Constraint:** Integrators must implement Null Safety on `dimensional_scores`, as legacy `v1` profiles will return `null` for these fields.
