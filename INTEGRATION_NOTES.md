# Integration Notes (Release 1.0)

**Guide for Frontend**
**Goal:** Safe, robust integration with the Multi-Agent Backend.

---

## 1. Happy Path Sequence

1.  **Ingest Brand Assets**
    *   Call `POST /ingest` (File or URL).
    *   *Result:* `profile_id` (Draft Mode).
    *   *UI:* Show "Analyzing Brand Voice..." spinner.

2.  **Ideation (Strategy)**
    *   Call `POST /ideation/ideate` with `brand_id` + `topic`.
    *   *Result:* `brief_id` + JSON Brief.
    *   *UI:* Render Brief for user review.

3.  **Approval (Gate)**
    *   Call `POST /pipeline/{id}/approve/ideation`.
    *   *Note:* Backend tracks approval state. This is required before execution.

4.  **Execution (Generation)**
    *   Call `POST /execute` with `brand_id` + `brief_id` + `platforms`.
    *   *Result:* Platform-specific copy.
    *   *UI:* Render tabs for each platform result.

---

## 2. Safety & Guards

### Do Not Assume Completeness
The AI is probabilistic. Required fields (keys) will exist, but their values might be "low quality" or empty.
*   **Example:** `seo_keywords` might be `[]`.
*   **Handling:** Hide the "Keywords" chip section if empty.

### Handling Latency
*   `POST /ingest` (PDFs): Can take **10-30 seconds**.
*   `POST /execute`: Can take **15-45 seconds**.
*   **Requirement:** Use long-running loading states. Do **NOT** timeout requests under 60s.

### Versioning (V1 vs V2)
*   The backend supports multiple agent versions simultaneously.
*   **Always** read `profile.version` before deciding which UI components to render.
*   *V1:* Human-readable rules only.
*   *V2:* Adds Dimensional Scores (Radar Chart).

---

## 3. Retry Policy
| Endpoint | Safe to Retry? | Limit |
| :--- | :--- | :--- |
| `/ingest` | ✅ YES | 1x (File uploads may flake) |
| `/ideation` | ✅ YES | 3x (Idempotent) |
| `/execute` | ⚠️ NO | Expensive. Prompt user to "Regenerate" manually. |
| `/approve` | ✅ YES | 3x |

---

## 4. Known Oddities (Release 1.0)
*   **Twitter Threads:** Sometimes return as a single string instead of an array.
    *   *Fix:* Frontend should split by newlines if `thread` is a string.
*   **Tone Description:** Sometimes redundant with Primary Tone.
    *   *Fix:* Dedup in UI if needed (e.g. "Professional (Professional style)").

---

## 5. Support
*   **Backend Owner:** AI Agent Backend Team
*   **Critical Issues:** `#backend-im-alerts`
*   **Non-Blocking Bugs:** File a Linear Ticket (Tag: `backend-v1`)
