# API Directory & Source Map

**Status:** Live / Development
**Base URL:** `http://localhost:8082`

This document maps all public API endpoints to their source code locations in the `adapters/api/routers` directory. Use this to locate the exact file responsible for handling a request.

---

## 🗺️ Router Map

| Base Prefix | Source File | Primary Responsibility |
| :--- | :--- | :--- |
| `/brands` | [`adapters/api/routers/brand_router.py`](../../adapters/api/routers/brand_router.py) | Brand entity creation and listing. |
| `/execute` | [`adapters/api/routers/execution_router.py`](../../adapters/api/routers/execution_router.py) | **Agent 3**: Generating platform content (Blog, LinkedIn, etc). |
| `/ideation` | [`adapters/api/routers/ideation_router.py`](../../adapters/api/routers/ideation_router.py) | **Agent 2**: Content Idea and Brief generation. |
| `/ingest` | [`adapters/api/routers/ingest_router.py`](../../adapters/api/routers/ingest_router.py) | **Agent 1**: Ingesting files/URLs to create Voice Profiles. |
| `/pipeline` | [`adapters/api/routers/orchestration_router.py`](../../adapters/api/routers/orchestration_router.py) | Orchestration: Starting pipelines, approving steps (`v2` flow). |
| `/profiles` | [`adapters/api/routers/feedback_router.py`](../../adapters/api/routers/feedback_router.py) | **Feedback Loop**: Submitting accept/reject stats for profiles. |
| `/voice` | [`adapters/api/routers/profile_router.py`](../../adapters/api/routers/profile_router.py) | **Voice Management**: Updating rules/tone for a specific brand. |
| `/profiles` | [`adapters/api/routers/voice_refinement_router.py`](../../adapters/api/routers/voice_refinement_router.py) | **Refinement**: Agent-1 V2 logic for refining V1 profiles into V2 Personas. |

---

## 📍 Detailed Endpoint Locations

### 1. Brand Management
*   **File:** `brand_router.py`
*   **Endpoints:**
    *   `POST /brands/create` - Create new brand.

### 2. Ingestion (Agent 1)
*   **File:** `ingest_router.py`
*   **Endpoints:**
    *   `POST /ingest` - Main entry point for file/URL ingestion.

### 3. Ideation (Agent 2)
*   **File:** `ideation_router.py`
*   **Endpoints:**
    *   `POST /ideation/ideate` - Generate content brief.
    *   `GET /ideation/briefs/{brand_id}` - List briefs.
    *   `GET /ideation/brief/{brief_id}` - Get specific brief.

### 4. Execution (Agent 3)
*   **File:** `execution_router.py`
*   **Endpoints:**
    *   `POST /execute` - Generate content.
    *   `GET /execute/health` - Health check.

### 5. Pipelines & Orchestration
*   **File:** `orchestration_router.py`
*   **Endpoints:**
    *   `POST /pipeline/start` - Initialize new pipeline state.
    *   `GET /pipeline/{pipeline_id}` - Get status.
    *   `POST /pipeline/{pipeline_id}/step/{step_name}/approve` - Gatekeeper.

### 6. Profile & Feedback
*   **Files:** `feedback_router.py`, `profile_router.py`
*   **Endpoints:**
    *   `POST /profiles/{id}/feedback` (`feedback_router.py`) - Record acceptance rate.
    *   `GET /profiles/{id}/stats` (`feedback_router.py`) - View stats.
    *   `PATCH /voice/{brand_id}/rules` (`profile_router.py`) - Edit tone/rules (Creates Draft).

### 7. Voice Refinement (Agent 1 V2)
*   **File:** `voice_refinement_router.py`
*   **Endpoints:**
    *   `POST /profiles/{profile_id}/refine` - Machine Refinement of a V1 profile.
