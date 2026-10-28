# Brand Voice Meta-Agent Platform - API Documentation
**Version:** 1.0.0 (Draft)
**Date:** February 16, 2026
**Status:** Production-Ready

---

## 1. API Overview

| Feature | Specification |
| :--- | :--- |
| **Base URL** | `http://<platform-host>:8000` |
| **Versioning** | URI-path versioning is *not* strictly used. Instead, **Parameter-based versioning** (`execution_version="v2"`) is used for specific endpoints. |
| **Authentication** | Assumed Bearer Token (Middleware not visible in provided context, but standard for production). |
| **Content Type** | `application/json` (Default), `multipart/form-data` (File Ingestion). |
| **Async Support** | Partial. Long-running tasks use direct `await` (Synchronous implementation for MVP/Cloud Run). `POST /ingest/async` is explicitly disabled (501). |

---

## 2. Endpoint Directory

| Method | Path | Purpose | Agent | Version | Sync/Async |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/ingest` | Ingest Text/URL/File for Voice Profiling | Agent 1 | V1 | Sync |
| **POST** | `/ingest/upload` | Legacy File Upload (PDF/Docx) | Agent 1 | V1 | Sync |
| **GET** | `/ingest/profile/{id}` | Get Voice Profile by ID | Agent 1 | V1 | Sync |
| **GET** | `/ingest/profiles/brand/{id}` | Get Output by Brand ID | Agent 1 | V1 | Sync |
| **POST** | `/ingest/approve/{id}` | Approve Voice Profile (Lock) | Agent 1 | V1 | Sync |
| **POST** | `/profiles/{id}/refine` | **Refine Voice Profile (Dimensional)** | Agent 1 | **V2** | Sync |
| **POST** | `/brands/create` | Create New Brand | Core | - | Sync |
| **DELETE** | `/brands/{id}/resources` | **Discard Session / Reset Brand** | Core | - | Sync |
| **POST** | `/ideation/ideate` | Generate Content Brief | Agent 2 | V1 | Sync |
| **GET** | `/ideation/briefs/{brand_id}` | List Content Briefs | Agent 2 | V1 | Sync |
| **POST** | `/execute` | Generate Final Content (Single/Multi) | Agent 3 | **V1/V2** | Sync |
| **GET** | `/execute/content/{brand_id}` | Get Generated Content | Agent 3 | V1/V2 | Sync |
| **POST** | `/profiles/{id}/feedback` | Submit Acceptance Logic | Core | - | Sync |
| **PATCH** | `/voice/{brand_id}/rules` | Manually Edit Voice Rules | Core | V1 | Sync |
| **GET** | `/voice/{brand_id}/personas` | List V2 Personas | Core | **V2** | Sync |
| **POST** | `/pipeline/start` | Initialize Pipeline State | Orch | - | Sync |
| **POST** | `/pipeline/regenerate/{id}` | Regenerate Voice Profile | Orch | V1 | Sync |

---

## 3. Detailed Endpoint Contracts

### 3.1. Ingestion (Agent 1)

#### **Ingest Content (Unified)**
*   **Method**: `POST`
*   **Path**: `/ingest`
*   **Description**: Analyzes text, URLs, or files to extract a Brand Voice Profile.
*   **Request (Multipart/Form-Data)**:
    *   `file`: Binary (PDF, DOCX, MP3, WAV, MP4)
    *   `brand_id`: UUID (Optional, auto-creates if missing)
*   **Request (JSON)**:
    ```json
    {
      "brand_name": "Acme Corp",
      "input_type": "url", // or "text"
      "input_value": "https://example.com/brand-voice"
    }
    ```
*   **Response (JSON)**:
    ```json
    {
      "brand_id": "uuid",
      "profile_id": "uuid",
      "status": "completed",
      "tone": {
        "primary": "Professional",
        "secondary": ["Authoritative"],
        "description": "..."
      },
      "dos": ["Use active voice"],
      "donts": ["No slang"],
      "best_match_examples": [
        {"example_id": "ex_1", "text": "..."}
      ]
    }
    ```

#### **Refine Profile (V2 Only)**
*   **Method**: `POST`
*   **Path**: `/profiles/{profile_id}/refine`
*   **Description**: Upgrades a V1 Profile to V2 by calculating Dimensional Scores and Implicit Rules.
*   **Response**:
    ```json
    {
      "status": "success",
      "profile_id": "uuid",
      "refinement": {
        "dimensional_scores": {"formality": 8, "empathy": 4},
        "implicit_rules": ["..."]
      }
    }
    ```

### 3.2. Ideation (Agent 2)

#### **Generate Brief**
*   **Method**: `POST`
*   **Path**: `/ideation/ideate`
*   **Description**: Generates a strategic content brief based on a topic. **Strictly isolated from Voice Profile**.
*   **Request**:
    ```json
    {
      "brand_id": "uuid",
      "topic": "AI in Healthcare",
      "market": "HealthTech",
      "region": "US"
    }
    ```
*   **Response**:
    ```json
    {
      "brief_id": "uuid",
      "content_brief": {
        "target_audience": "Hospital Admins",
        "seo_keywords": ["AI diagnostics"],
        "h2_outline": ["Intro", "Benefits", "Case Studies"],
        "key_takeaways": ["Efficiency up 20%"]
      },
      "constraints": {
        "voice_profile_id": "uuid",
        "must_follow_voice": true
      }
    }
    ```

### 3.3. Execution (Agent 3)

#### **Execute Content Generation**
*   **Method**: `POST`
*   **Path**: `/execute`
*   **Description**: Generates final marketing copy. Supports V1 (Single Voice) and V2 (Multi-Persona).
*   **Request (Auto-Fetch)**:
    ```json
    {
      "brand_id": "uuid",
      "platforms": ["blog", "linkedin"],
      "execution_version": "v1" // or "v2"
    }
    ```
*   **Request (V2 Specific)**:
    ```json
    {
      "brand_id": "uuid",
      "platforms": ["linkedin"],
      "execution_version": "v2",
      "persona_ids": ["persona_uuid_1", "persona_uuid_2"]
    }
    ```
*   **Response**:
    ```json
    {
      "blog": { "title": "...", "content": "..." },
      "linkedin": { "post": "..." },
      "twitter": { "thread": ["...", "..."] },
      "email": { "subject": "...", "body": "..." }
    }
    ```
    *Note: For V2 with multiple personas, returns a Dict keyed by persona_id.*

### 3.4. Orchestration & State

#### **Regenerate Voice Profile**
*   **Method**: `POST`
*   **Path**: `/pipeline/regenerate/{incoming_id}`
*   **Description**: Triggers a re-run of Agent 1 for a brand. `incoming_id` can be `brand_id` or `profile_id`.
*   **Behavior**: Creates a NEW version. Does not overwrite history.

#### **Discard Session (Reset)**
*   **Method**: `DELETE`
*   **Path**: `/brands/{brand_id}/resources`
*   **Description**: **Destructive**. Deletes all Profiles, Personas, Briefs, and Generated Content for the brand. Brand ID preserves.

---

## 4. Pipeline State Machine

The logic is managed by `PipelineStateRepo` and `PipelineRunner`.

| State | transitions To | Trigger |
| :--- | :--- | :--- |
| **NOT_STARTED** | INGESTING | `POST /pipeline/start` |
| **INGESTING** | VOICE_READY | Agent 1 Completion |
| **VOICE_READY** | BRIEF_READY | Agent 2 Completion |
| **BRIEF_READY** | EXECUTING | `POST /execute` |
| **EXECUTING** | COMPLETED | Agent 3 Completion |
| **COMPLETED** | REFINED | `POST /profiles/.../refine` |
| *ANY* | FAILED | Exception |

**Approval States (per Step)**:
*   `PENDING` -> `APPROVED`
*   `PENDING` -> `REJECTED` -> `PENDING` (on Retry)

---

## 5. Version Differentiation

| Feature | **V1 (Legacy/Stable)** | **V2 (Advanced)** |
| :--- | :--- | :--- |
| **Ingestion** | Text/URL -> Flat Rules | Same |
| **Profile Structure** | `dos`, `donts`, `tone` | V1 + `dimensional_scores` + `implicit_rules` |
| **Personas** | Single Voice Profile | Multiple Personas (`PersonaManager`) |
| **Execution** | Single Output | Multi-Persona Output |
| **API Param** | `execution_version="v1"` | `execution_version="v2"` |

**V2-Only Endpoints**:
*   `POST /profiles/{id}/refine`
*   `GET /voice/{brand_id}/personas`

---

## 6. Feedback Loop Contract

The system enforces a **closed-loop feedback mechanism**:

1.  **Metric Collection**: `POST /profiles/{id}/feedback` (`action`: accept/reject/rewrite).
2.  **Stat Updates**: Updates `acceptance_rate` and `rewrite_count` in the Profile JSON.
3.  **Manual Override**: `PATCH /voice/{brand_id}/rules` allows users to explicitly fix rules. This creates a **New Version** of the profile but resets approval stats.

---

## 7. Integration Checklist for Platform Team

1.  **Ingestion Latency**: Analysis can take 10-30s. Ensure frontend shows a spinner/progress bar. Use `POST /pipeline/start` to track state if needed.
2.  **V2 Migration**: To use V2 features, you **MUST** call `/profiles/{id}/refine` on existing V1 profiles first.
3.  **Error Handling**:
    *   `404 Brand Not Found`: Restart flow.
    *   `501 Not Implemented`: Async endpoints are disabled in this environment.
4.  **Persistence**:
    *   Agent 1 & 2 outputs are *always* persisted by default.
    *   Agent 3 output can be ephemeral (session-based) or persisted (`save_to_db=true`).
5.  **Clean Reset**: Use `DELETE /brands/{id}/resources` to allow users to "Start Over" without losing their Brand Name/ID.

---

## 8. Audit & Recommendations

### A. Missing Endpoints
*   `GET /brands`: List all brands (currently only Create/Delete-Resources exists).
*   `GET /pipeline/{brand_id}`: Get active pipeline by Brand ID (currently requires Pipeline ID).

### B. Redundant Endpoints
*   `POST /ingest/upload`: Superseded by unified `POST /ingest` (Multipart support).
*   `POST /voice/{brand_id}/feedback` (in `profile_router`): Redundant with `POST /profiles/{id}/feedback` (in `feedback_router`). **Recommendation:** Deprecate `profile_router` version.

### C. API Improvements
*   **Standardize Response Envelopes**: Some endpoints return raw objects, others return `{"status": "success", ...}`.
*   **Unified Error Codes**: Define explicit string codes (e.g., `ERR_PROFILE_LOCKED`) instead of just HTTP status.

### D. Security Hardening
*   **Input Sanitization**: `ingest` endpoint accepts raw URLs. Ensure SSRF protection is enabled (currently relies on `requests` lib defaults).
*   **Rate Limiting**: Not observed. Heavy LLM calls should be rate-limited per Brand/IP.

### E. Observability
*   **Trace IDs**: `Agent3Request` supports `trace_id`, but it's not consistently propagated to V1 agents.
*   **Cost Tracking**: No visible token usage/cost tracking in response metadata.
