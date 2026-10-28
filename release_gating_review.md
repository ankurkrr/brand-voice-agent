# Release Gating Review: AI Backend Platform

**Date:** 2026-01-30
**Reviewer:** Principal Platform Engineer (Agent)
**Status:** **RELEASE CANDIDATE**

## 1. API CONTRACT STABILITY
| Endpoint | Stability | Verdict |
| :--- | :--- | :--- |
| `POST /ingest` | 🟢 Stable | Request/Response schemas are backward compatible. `skip_generation` flag allows staged processing. Hybrid V1/V2 outputs normalized. |
| `POST /pipeline/start` | 🟢 Stable | Deterministic `PipelineState` response. |
| `POST /pipeline/{id}/step/*` | 🟢 Stable | Step execution order enforced by `PipelineRunner`. |
| `POST /ideation/ideate` | 🟢 Stable | Clear input/output contract. Fingerprinting ensures idempotency. |
| `POST /execute` | ⚠️ **Fragile** | Response schema is stable, but **internal hydration logic** is manually coupled to DB schema. Regression risk if underlying tables change. |

## 2. CONTRACT FREEZE (Canonical)

The following schemas are **FROZEN** for Release 1.0.

### Agent 1 (Voice Profile) - V2
*   **REQUIRED:** `brand_id`, `version` ("v1"|"v2"), `status` ("DRAFT"|"APPROVED")
*   **OPTIONAL:** `dimensional_scores` (May be NULL for legacy V1)
*   **STRUCTURE:**
    *   `rules`: { `dos`: string[], `donts`: string[], `forbidden_phrases`: string[] }
    *   `tone`: { `primary`: string, `description`: string } (Extracted to top-level)

### Agent 2 (Content Brief)
*   **REQUIRED:** `brief_id`, `topic`
*   **REQUIRED:** `content_brief` object (may contain empty strings/arrays)
*   **STRUCTURE:**
    *   `content_brief`: { `target_audience`: string, `key_takeaways`: string[], `h2_outline`: string[] }
    *   `constraints`: { `voice_profile_id`: string }

### Agent 3 (Execution)
*   **REQUIRED:** `raw_json`
*   **OPTIONAL:** `blog`, `linkedin`, `twitter`, `email` (Keys exist only if requested)
*   **NULL SAFETY:** Frontend must handle missing platform keys using optional chaining (e.g., `res.twitter?.thread`).

## 3. NULL & EMPTY SAFETY
*   **Principle:** `NULL` = "Data Not Available" (Not System Failure).
*   **Frontend Requirements:**
    *   **Dimensional Scores:** Must check for `null` before rendering Radar Chart.
    *   **Lists:** Must handle empty arrays `[]` (e.g., secondary tones, forbidden phrases).
    *   **Text:** Must handle empty strings `""` (e.g., tone description).
*   **Guarantee:** The backend will **never crash** due to missing internal AI data; it will return valid JSON with nulls/empty values.

## 4. ORCHESTRATION SAFETY
*   ✅ **Pipeline Integrity:** Steps cannot run out of order.
*   ✅ **Approvals:** Gating logic (`approve_step`) correctly transitions state to `APPROVED`.
*   ✅ **Persistence:** All artifacts are persisted to DB before returning to client (except ephemeral tests).
*   ✅ **Concurrency:** `POST /ideation/ideate` handles parallel requests via safe read-only brand checks.

## 5. VERSIONING & BACKWARD COMPATIBILITY
*   **V1 Compatibility:** Preserved. V1 agents continue to output legacy schemas.
*   **V2 Isolation:** V2 logic isolated in `core/agents/v2/`.
*   **Hybrid Support:** Ingestion pipeline normalized to handle "Hybrid V1" agents (V1 logic + V2 scores).
*   **Strategy:** Platform separates logic based on `profile.version`.

## 6. INTEGRATION RISKS
*   **Tech Debt:** Manual object hydration in `execution_router.py` (Line 66-194). **Action:** Monitor for regressions if `VoiceProfilesRepo` changes.
*   **V2 Rollout:** V2 agents are strictly "Refinement" agents. Do not use for initial creation unless `parent_profile` exists.
*   **Non-Blocker:** AI output quality (semantic completeness) is out of scope for this review.

---

## FINAL DECISION

# ⚠️ SAFE WITH GUARDS

**The backend is stable and adheres to contracts.**
Integration may proceed provided the Frontend implements the **Null/Empty Safety** requirements listed in Section 3.
