# MCP Server Handoff Guide — Brand Voice Agent

> **For:** Platform Team building the MCP Server
> **From:** Agent Backend Team
> **Date:** 2026-02-19

---

## Architecture Overview

```
Platform Side (YOU build)              Agent Side (WE provide)
┌──────────────────────────┐          ┌──────────────────────────┐
│  org_id + user_id        │          │  FastAPI Backend          │
│        │                 │          │                          │
│        ▼                 │          │  POST /pipeline/start    │
│  MCP Server              │ ──HTTP──▶│  POST /pipeline/{id}/step│
│  (wraps our API)         │          │  POST /pipeline/{id}/approve│
│  Passes org_id as        │          │  GET  /pipeline/{id}/state│
│    brand_id directly     │          │                          │
│  Stores results in your DB│         │  Our DB tracks pipeline  │
│  Surfaces as MCP tools   │          │  state internally        │
└──────────────────────────┘          └──────────────────────────┘
```

**No middleware needed from our side.** The MCP server IS the middleware — and you build it.

---

## Deliverables Checklist (What We Share)

| # | Asset | Format | Description |
|---|-------|--------|-------------|
| 1 | `openapi.json` | OpenAPI 3.1 | Full API spec, auto-generated from FastAPI |
| 2 | `platform_postman_collection.json` | Postman v2.1 | All endpoints with realistic sample payloads/responses |
| 3 | `PLATFORM_API_CONTRACT_v1.0.md` | Markdown | Canonical data contracts & schemas |
| 4 | `INTEGRATION_NOTES.md` | Markdown | Retry policies, latency, known quirks |
| 5 | Deployed Base URL | URL | Cloud Run endpoint (shared separately) |

---

## Pipeline Flow (Recommended Integration Path)

Use `POST /pipeline/start` for server-side orchestration. This handles chaining for you.

### Happy Path Sequence

```
Step 1: POST /brands/create            → Returns brand_id
           body: { name: "OrgName", brand_id: "your-org-id" }
           (pass your org_id as brand_id — no mapping needed!)

Step 2: POST /pipeline/start            → Returns pipeline_id
           ?brand_id=your-org-id&mode=v1

Step 3: POST /pipeline/{id}/step/voice_profiling  ⏱ 10-30s
           body: { input_type: "url", input_value: "https://..." }

Step 4: POST /pipeline/{id}/approve/voice_profiling
           body: { feedback: "optional" }

Step 5: POST /pipeline/{id}/step/ideation          ⏱ 5-15s
           body: { topic: "AI in Healthcare", market: "..." }

Step 6: POST /pipeline/{id}/approve/ideation

Step 7: POST /pipeline/{id}/step/execution         ⏱ 15-45s
           body: { platforms: ["blog","linkedin","twitter","email"] }

Step 8: GET /pipeline/{id}/state         → Final state with all artifact IDs
```

### ID Mapping (org_id = brand_id)

> **You can pass your `org_id` directly as `brand_id` in `POST /brands/create`.** No mapping table needed.

| Your Side | Our Side | How |
|-----------|----------|-----|
| `org_id` | `brand_id` | Pass your `org_id` as the `brand_id` field in `/brands/create`. It becomes the brand_id everywhere. |
| `user_id` | N/A | We don't track users. Store `user_id` ↔ actions in your DB |
| `pipeline_id` | `pipeline_id` | Returned from `/pipeline/start`. Use for all step/approve calls |

**Example:**
```
POST /brands/create
body: { name: "Acme Corp", brand_id: "org_12345" }

→ Returns: { brand_id: "org_12345", name: "Acme Corp", ... }

# Now use "org_12345" everywhere:
POST /pipeline/start?brand_id=org_12345
POST /ingest  body: { brand_id: "org_12345", ... }
```

---

## Critical Behavior Notes

### Latency (Set timeouts ≥ 60s)
| Endpoint | Latency |
|----------|---------|
| `/pipeline/step/voice_profiling` | 10-30s |
| `/pipeline/step/ideation` | 5-15s |
| `/pipeline/step/execution` | 15-45s |
| All other endpoints | < 2s |

### Retry Safety
| Endpoint | Safe to Retry? |
|----------|---------------|
| `/brands/create` | ✅ Yes |
| `voice_profiling` step | ✅ Yes |
| `ideation` step | ✅ Yes (fingerprint-based dedup) |
| `execution` step | ❌ **NO** (expensive LLM calls) |

### Versioning
- Voice profiles support `v1` (basic) and `v2` (adds `dimensional_scores` for radar charts)
- Check `version` field in profile response to determine which fields to render
- `v2` profiles include `dimensional_scores` and `implicit_rules`

### Pipeline State Machine
```
IDLE → IN_PROGRESS → COMPLETED
                   → FAILED

Step states: PENDING → RUNNING → COMPLETED / FAILED / SKIPPED
```

---

## MCP Tool Definitions (Suggested Mapping)

### Core Tools (Pipeline-Based)
| MCP Tool Name | HTTP Call | Purpose |
|--------------|-----------|---------|
| `create_brand` | `POST /brands/create` | Create brand using platform's org_id as brand_id |
| `start_pipeline` | `POST /pipeline/start` | Initialize pipeline |
| `run_voice_profiling` | `POST /pipeline/{id}/step/voice_profiling` | Run Agent 1 |
| `approve_voice_profile` | `POST /pipeline/{id}/approve/voice_profiling` | Approve profile |
| `run_ideation` | `POST /pipeline/{id}/step/ideation` | Run Agent 2 |
| `approve_ideation` | `POST /pipeline/{id}/approve/ideation` | Approve brief |
| `run_execution` | `POST /pipeline/{id}/step/execution` | Run Agent 3 |
| `get_pipeline_state` | `GET /pipeline/{id}/state` | Check progress |

### Supporting Tools
| MCP Tool Name | HTTP Call | Purpose |
|--------------|-----------|---------|
| `get_voice_profile` | `GET /ingest/profile/{profile_id}` | Fetch profile details |
| `get_content_brief` | `GET /ideation/brief/{brief_id}` | Fetch brief details |
| `get_generated_content` | `GET /execute/content/{brand_id}` | Fetch generated copy |
| `submit_feedback` | `POST /profiles/{id}/feedback` | Record accept/reject/rewrite |
| `regenerate_profile` | `POST /pipeline/regenerate/{id}` | Force new profile |
| `reject_step` | `POST /pipeline/{id}/reject/{step}` | Reject artifact |
| `delete_brand_resources` | `DELETE /brands/{id}/resources` | Reset brand |

---

## Error Contract

All errors follow this structure:
```json
{
  "detail": "Human-readable error message"
}
```

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad input (missing fields, invalid state) |
| 404 | Resource not found (bad brand_id, profile_id, etc.) |
| 422 | Validation error (Pydantic schema mismatch) |
| 500 | Internal server error |

---

## Questions for Platform Team

1. **Auth:** How will the MCP server authenticate against our API? (API key, OAuth, etc.)
2. **Webhooks:** Do you need us to add webhook callbacks for long-running steps?
3. **Rate limits:** What throughput do you expect? (helps us size Cloud Run instances)
