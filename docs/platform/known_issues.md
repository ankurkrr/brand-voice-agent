# Known Issues (Non-Blocking)

**Status:** Acknowledged & Monitored
**Impact:** Minor / Edge Case

These issues are part of the Release 1.0 baseline. They do **not** block integration.

---

## 1. Dimensional Scores may be Null
*   **Context:** Agent 1 V1 (legacy) and some Hybrid V1 agents do not generate scores.
*   **Behavior:** `dimensional_scores: null` in API response.
*   **Mitigation:** Frontend must guard chart rendering.

## 2. Hybrid Ingestion Paths
*   **Context:** The system supports both V1 and V2 pathways.
*   **Behavior:** You may receive a `v2` marked profile that is functionally similar to `v1`.
*   **Mitigation:** Trust the `version` flag, but always check data presence.

## 3. Execution Hydration is Manual
*   **Context:** The `POST /execute` endpoint manually maps DB JSON to internal models.
*   **Risk:** If DB schema changes, this endpoint might break before valid update.
*   **Mitigation:** Backend team monitors this closely. No action needed from frontend.

## 4. Latency
*   **Context:** AI inference is slow.
*   **Behavior:** `/ingest` and `/execute` can take 30s+.
*   **Mitigation:** UI must strictly handle loading states and NOT timeout < 60s.

## 5. Duplicate Tones
*   **Context:** Sometimes `primary` tone is repeated in `secondary`.
*   **Behavior:** Tone: "Professional (Professional, Concise)".
*   **Mitigation:** Frontend deduplication logic (optional).
