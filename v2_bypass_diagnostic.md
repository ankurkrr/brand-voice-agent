# Diagnostic Report: Agent 1 V2 Persistent Empty Output

**Issue:**
Agent 1 V2 outputs (dim scores, implicit rules) remain null/empty despite the fix applied in `PipelineRunner`.

**Root Cause Verification:**
The system has **two distinct execution paths** for Agent 1. The fix was applied to one, but the user is likely testing the other.

1.  **Pipeline Orchestration Path (FIXED)**
    -   **Entry:** `POST /pipeline/{id}/step/voice_profiling`
    -   **Code:** `adapters/api/routers/orchestration_router.py` -> `PipelineRunner._run_voice_profiling`
    -   **Status:** **Correct**. This path uses the adapter logic I added, mapping and persisting the V2 data properly.

2.  **Ingestion/Direct Generation Path (BROKEN)**
    -   **Entry:** `POST /ingest` or `POST /ingest/generate/{brand_id}`
    -   **Code:** `adapters/api/routers/ingest_router.py` -> `ingest_content` / `generate_voice_profile`
    -   **Status:** **Broken**. This path **bypasses** `PipelineRunner` entirely. It calls the ingestion logic which likely invokes `Agent 1` directly without the V2 adapter, sending raw output to `VoiceProfilesRepo`.
    -   Since `VoiceProfilesRepo` expects legacy keys (`rules`, `style_metrics`), the V2 keys (`refined_explicit_rules`, `implicit_rules`) are ignored, resulting in null values in the database.

**Conclusion:**
The fix is functionally correct for the **Pipeline Runner**, but the Ingestion Router (used for initial creation/testing) proceeds through an unpatched legacy codepath (`core/pipelines/ingestion.py`).

**Required Follow-up (Not applied):**
To fix this, the **Ingestion Pipeline (`core/pipelines/ingestion.py`)** must also be updated with the same V2 Output Adapter logic used in `PipelineRunner`.
