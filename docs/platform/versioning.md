# Platform Versioning Strategy

**Core Concept:** The backend supports **Hybrid Versioning**.
Old V1 profiles and new V2 profiles coexist in the same database.

## The `version` Flag

Every `VoiceProfile` object contains a literal version field:

```json
{
  "version": "v1" | "v2"
}
```

**Frontend Responsibility:**
You MUST branch your UI rendering logic based on this flag.

---

## 🆚 Comparison

| Feature | V1 (Legacy) | V2 (Standard) |
| :--- | :--- | :--- |
| **Rules Engine** | Text-based Only | Text + Numeric Scores |
| **Dimensional Scores** | `null` (Always) | Object (Radar Chart Data) |
| **Tone Structure** | Flat string dict | Structured Object |
| **Persona Support** | Single Brand Voice | Multi-Persona (Parent/Child) |

---

## 🚦 Integration Rules

### 1. Rendering Radar Charts
*   **V1:** Do NOT render the chart. Show text tone only.
*   **V2:** Render chart. *Guard:* Check if `dimensional_scores !== null` first (Hybrid case).

### 2. Updating Profiles
*   `PATCH /voice/{id}/rules` will create a **DRAFT** version.
*   The version number may increment (e.g. `v2` -> `v2.1` internal, but API sees `v2`).

### 3. Execution Compatibility
*   Agent 3 (Execution) is **Version Agnostic**.
*   It works with both V1 and V2 profiles transparently.
*   No frontend changes needed for execution flow.
