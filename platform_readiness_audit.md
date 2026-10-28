# Platform Readiness Audit: AI Backend Integration

**Date:** 2026-01-30
**Auditor:** Principal Platform Engineer (Agent)
**Scope:** Agent 1 (V1/V2), Agent 2, Agent 3, API Layer, Orchestration

## 1. Executive Summary (Platform View)
The system is **SAFE TO INTEGRATE WITH GUARDS.**
The core orchestration (PipelineRunner) and defined agent contracts are stable. However, the **Execution Router (`/execute`)** contains brittle hydration logic that poses a high integration risk if the data schema evolves. Backward compatibility for V1/V2 execution is now functional (post-fix), but the frontend must strictly respect `version` flags to avoid rendering empty V2 components for V1 data.

**Decision:** ⚠️ **PROCEED WITH GUARDS**

---

## 2. API Stability Verdict

| Endpoint | Stability | Risk Factors |
| :--- | :--- | :--- |
| `POST /ingest` | 🟢 Stable | `skip_generation` flag logic is robust. Hybrid V1/V2 outputs are now normalized. |
| `POST /pipeline/start` | 🟢 High | Strict `PipelineState` output. |
| `POST /ideation/ideate` | 🟢 High | Clear boundary. `save_to_db` flag allows safe validation. |
| `POST /execute` | 🔴 **Risky** | **Hydration Logic:** Lines 66-194 map DB JSON manually to internal models. If DB schema changes, this breaks. |
| `GET /pipeline/{id}/state` | 🟢 High | Immutable state object. |

---

## 3. Frozen Contracts (Canonical)

These contracts are now **FROZEN**. Any change requires a V3 version.

### Agent 1: Voice Profile (V2)
```typescript
interface VoiceProfile {
  id: string; // UUID
  brand_id: string;
  version: "v1" | "v2";
  status: "DRAFT" | "APPROVED";
  
  // V2 Specific (May be NULL in V1)
  dimensional_scores: {
    humor: float;
    empathy: float;
    authority: float;
    formality: float;
    urgency: float;
  } | null;

  rules: {
    dos: string[];
    donts: string[];
    forbidden_phrases: string[];
  };

  tone: {
    primary: string;
    secondary: string[];
    description: string;
  };
}
```

### Agent 2: Content Brief
```typescript
interface ContentBrief {
  brief_id: string; // UUID
  topic: string;
  status: "generated";
  
  content_brief: {
    target_audience: string;
    key_takeaways: string[];
    seo_keywords: string[];
    h2_outline: string[]; // List of strings
    cta: string;
  };
  
  constraints: {
    voice_profile_id: string;
    must_follow_voice: boolean;
  };
}
```

### Agent 3: Execution Output
```typescript
interface ExecutionOutput {
  id?: string;
  
  // Platforms (Keys may be missing if not requested)
  blog?: { title: string; body: string };
  linkedin?: { text: string };
  twitter?: { thread: string[] };
  email?: { subject: string; body: string };
  
  raw_json: object; // Full debug payload
}
```

---

## 4. Null & Empty Value Safety
**Platform Rule:** Treat `null` as "Data Unavailable", NOT "System Error".

*   **Dimensional Scores:**
    *   **Risk:** Can be `null` (Legacy V1 profiles).
    *   **Guard:** Frontend Radar Chart MUST check `if (scores)` before rendering. If null, hide chart (do not crash).
*   **Platform Content:**
    *   **Risk:** `twitter` key missing if user only selected `blog`.
    *   **Guard:** Frontend must use optional chaining `result.twitter?.thread`.
*   **Tone:**
    *   **Risk:** `secondary` tones might be an empty array `[]`.
    *   **Guard:** Join logic should handle empty lists safely.

---

## 5. Integration Safety Guarantees
1.  **Orchestration Integrity:**
    *   `PipelineRunner` prevents skipped steps. You cannot run Agent 3 without Agent 2 completion.
2.  **Idempotency:**
    *   `POST /ideation/ideate` checks fingerprints to avoid duplicates (safe to retry).
    *   `POST /ingest` updates existing brands (safe to retry).
3.  **V2 Isolation:**
    *   V2 logic is isolated in `core/agents/v2/`.
    *   Legacy V1 path is preserved via `version` flag.

---

## 6. Required Shims (Frontend)
To integrate safely, the frontend **MUST** implement:

1.  **Version Shim:**
    ```javascript
    const isV2 = (profile) => profile.version === 2 || profile.version === "v2";
    ```
2.  **Score Normalizer:**
    ```javascript
    const getScores = (profile) => isV2(profile) ? profile.dimensional_scores : DEFAULT_SCORES;
    ```

---

## 7. Risk Register
*   **HIGH:** `execution_router.py` manual hydration. This needs a tech debt ticket to be refactored into a shared Domain Service.
*   **MEDIUM:** Hybrid V1 agents (V1 + partial V2 output) exist in non-prod envs. Fixed by ingestion adapter, but monitoring needed.
*   **LOW:** Large payload sizes for 50+ page PDFs might timeout `POST /ingest`. Recommend async polling for large files.

## 8. Go / No-Go Decision

✅ **GO for Integration**
*   **Condition:** Frontend implements required Null Guards.
*   **Condition:** No changes to `adapters/api/` schemas without backend approval.
