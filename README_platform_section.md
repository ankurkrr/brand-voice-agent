## Platform Integration Readiness (Release 1.0)

**Status:** ⚠️ SAFE WITH GUARDS

The AI Backend (Agent 1, 2, 3) is released for integration. The system is stable, idempotent, and enforces strict version contracts.

### System Summary
The backend orchestrates a 3-step linear pipeline:
1.  **Ingestion (Agent 1):** Converts documents/URLs into a **Voice Profile**.
2.  **Ideation (Agent 2):** Converts a topic into a **Content Brief**.
3.  **Execution (Agent 3):** Converts Voice + Brief into **Platform Copy**.

### Base Assumptions
*   **Async-ish Latency:** Requests take 10s+. UI must handle loading states.
*   **Probabilistic Data:** AI outputs may vary safely. Required keys are guaranteed; values are not.
*   **Stateful:** Approvals (`POST /approve`) are required to move between steps.

### Versioning (V1 vs V2)
We currently support a hybrid V1/V2 environment.
*   **V1 Agents:** Produce text-heavy rules.
*   **V2 Agents:** Produce dimensional scores (radar metrics).
*   **Frontend Rule:** Check `version` field on Voice Profile to toggle UI components.

### Non-Blocking Known Issues
*   **Manual Hydration:** The Execution API (`POST /execute`) logic is manually coupled to DB schemas. This is stable for now but tracked as tech debt.
*   **Empty Scores:** Some legacy profiles will have `null` dimensional scores. See `NULL_SAFETY_GUIDE.md`.

### Owner
**Platform Engineering Team**
*   Docs: `/docs/platform`
*   Contract: `PLATFORM_API_CONTRACT_v1.0.md`
