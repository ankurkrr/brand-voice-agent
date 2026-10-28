# 📮 Postman API Testing Guide

**Version:** 1.0  
**Base URL (Local):** `http://localhost:8000`  
**Base URL (Cloud Run):** `https://<your-cloud-run-url>`  
**Content-Type:** `application/json` (unless noted otherwise)

---

## 📋 Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Health Check](#2-health-check)
3. [Brand Management](#3-brand-management)
4. [Agent 1 – Voice Profile Ingestion](#4-agent-1--voice-profile-ingestion)
5. [Agent 2 – Content Ideation](#5-agent-2--content-ideation)
6. [Agent 3 – Content Execution](#6-agent-3--content-execution)
7. [Pipeline Orchestration](#7-pipeline-orchestration)
8. [Voice Profile Management](#8-voice-profile-management)
9. [Feedback Loop](#9-feedback-loop)
10. [End-to-End Test Flow](#10-end-to-end-test-flow)

---

## 1. Environment Setup

### Postman Variables

Create a Postman Environment called `Voice Meta Agent` with these variables:

| Variable | Initial Value | Description |
|---|---|---|
| `base_url` | `http://localhost:8000` | API base URL |
| `brand_id` | *(empty)* | Auto-filled after brand creation |
| `profile_id` | *(empty)* | Auto-filled after ingestion |
| `brief_id` | *(empty)* | Auto-filled after ideation |
| `pipeline_id` | *(empty)* | Auto-filled after pipeline start |

> **Tip:** Use Postman's **Tests** tab to auto-save IDs. Example script:
> ```javascript
> var json = pm.response.json();
> pm.environment.set("brand_id", json.brand_id);
> ```

---

## 2. Health Check

### `GET /health`
**Purpose:** Verify the API server is running.

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/health` |
| Auth | None |

**Expected Response (200):**
```json
{
  "status": "ok"
}
```

### `GET /execute/health`
**Purpose:** Verify Agent 3 subsystem is alive.

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/execute/health` |

**Expected Response (200):**
```json
{
  "status": "ok",
  "agent": "agent3"
}
```

---

## 3. Brand Management

### 3.1 Create Brand

`POST /brands/create`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/brands/create` |
| Body Type | **x-www-form-urlencoded** |

> ⚠️ This endpoint uses **form data**, NOT JSON.

**Body (x-www-form-urlencoded):**

| Key | Value | Required |
|---|---|---|
| `name` | `Acme Corp` | ✅ |
| `brand_id` | `org-platform-123` | ❌ (auto-generated UUID if omitted) |

**Expected Response (200):**
```json
{
  "brand_id": "org-platform-123",
  "name": "Acme Corp",
  "created_at": "2026-02-19T15:00:00Z"
}
```

**Post-Request Script:**
```javascript
var json = pm.response.json();
pm.environment.set("brand_id", json.brand_id);
```

---

### 3.2 Delete Brand Resources

`DELETE /brands/{brand_id}/resources`

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `{{base_url}}/brands/{{brand_id}}/resources` |

**Expected Response (200):**
```json
{
  "status": "success",
  "message": "All brand resources discarded."
}
```

> **Note:** This deletes all generated profiles, briefs, personas, and content — but keeps the brand record itself for reuse.

---

## 4. Agent 1 – Voice Profile Ingestion

### 4.1 Ingest via Text/URL (JSON)

`POST /ingest`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ingest` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "brand_name": "Acme Corp",
  "input_type": "text",
  "input_value": "At Acme Corp, we believe in empowering businesses through innovative AI solutions. Our platform processes 10 million transactions daily with 99.9% uptime. We speak directly, use active voice, and keep things concise. Data security follows ISO 27001 standards. All transmissions use AES-256 encryption. Integration requires three steps: authentication, configuration, deployment. We never use jargon without context. We avoid exclamation marks and never start with questions."
}
```

**Alternative — URL Ingestion:**
```json
{
  "brand_name": "Acme Corp",
  "input_type": "url",
  "input_value": "https://www.example.com/about"
}
```

**Expected Response (200):**
```json
{
  "brand_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "profile_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "status": "generated",
  "version": 1,
  "tone": {
    "primary": "Professional",
    "secondary": ["Analytical", "Authoritative"],
    "description": "Fact-based and direct communication"
  },
  "dos": [
    "Use active voice",
    "Lead with data",
    "Keep sentences under 20 words"
  ],
  "donts": [
    "Avoid exclamation marks",
    "Don't use jargon without context",
    "Never start with questions"
  ],
  "best_match_examples": [
    {
      "example_id": "ex_1",
      "text": "Our platform processes 10M transactions daily. Performance metrics show 99.9% uptime."
    },
    {
      "example_id": "ex_2",
      "text": "Data security follows ISO 27001 standards. All transmissions use AES-256 encryption."
    },
    {
      "example_id": "ex_3",
      "text": "Integration requires three steps: authentication, configuration, deployment."
    }
  ],
  "raw_json": { ... },
  "profile_data": { ... }
}
```

**Post-Request Script:**
```javascript
var json = pm.response.json();
pm.environment.set("brand_id", json.brand_id);
pm.environment.set("profile_id", json.profile_id);
```

---

### 4.2 Ingest via File Upload

`POST /ingest/upload`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ingest/upload` |
| Body Type | **form-data** |

**Body (form-data):**

| Key | Type | Value | Required |
|---|---|---|---|
| `file` | File | Select a `.pdf` or `.docx` file | ✅ |
| `brand_id` | Text | `{{brand_id}}` | ✅ |
| `brand_name` | Text | `Acme Corp` | ❌ |
| `skip_generation` | Text | `false` | ❌ (default: `false`) |

> Set `skip_generation=true` to ingest content without generating the voice profile immediately. Use the Generate Profile endpoint (4.3) later.

---

### 4.3 Generate Profile (Staged Flow)

`POST /ingest/generate/{brand_id}`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ingest/generate/{{brand_id}}` |

> Use after ingesting with `skip_generation=true`.

---

### 4.4 Get Voice Profile by ID

`GET /ingest/profile/{profile_id}`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/ingest/profile/{{profile_id}}` |

**Expected Response (200):**
```json
{
  "id": "yyyyyyyy-...",
  "brand_id": "xxxxxxxx-...",
  "version": 1,
  "status": "DRAFT",
  "profile_data": {
    "tone": { "primary": "Professional", "secondary": [...], "description": "..." },
    "rules": { "dos": [...], "donts": [...] },
    "best_match_examples": [...],
    "system_prompt": "..."
  }
}
```

---

### 4.5 Get Voice Profile by Brand

`GET /ingest/profiles/brand/{brand_id}`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/ingest/profiles/brand/{{brand_id}}` |

> Returns the most recent voice profile for the brand.

---

### 4.6 Approve Profile

`POST /ingest/approve/{profile_id}`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ingest/approve/{{profile_id}}` |

> Transitions profile from `DRAFT` → `APPROVED`. This is the authoritative "Save" action.

---

### 4.7 Update Profile (Human Edit)

`POST /ingest/profile/{profile_id}/update`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ingest/profile/{{profile_id}}/update` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "system_prompt": "You are a professional brand voice assistant for Acme Corp...",
  "rules": {
    "dos": ["Use active voice", "Lead with data", "Be concise"],
    "donts": ["Avoid jargon", "No exclamation marks"]
  }
}
```

---

## 5. Agent 2 – Content Ideation

### 5.1 Generate Content Brief

`POST /ideation/ideate`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ideation/ideate` |
| Content-Type | `application/json` |
| Query Params | `save_to_db=true` (default), `regenerate=false` (default) |

**Body (JSON):**
```json
{
  "brand_id": "{{brand_id}}",
  "topic": "AI in Healthcare",
  "market": "Healthcare",
  "region": "North America",
  "content_goal": "Thought leadership"
}
```

> **Minimum required fields:** `brand_id` + `topic`

**Expected Response (200):**
```json
{
  "brief_id": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
  "content_brief": {
    "target_audience": "Healthcare administrators evaluating AI adoption",
    "seo_keywords": ["AI diagnostics", "healthcare AI", "medical imaging AI"],
    "h2_outline": [
      "AI Diagnostic Applications",
      "Data Privacy Considerations",
      "Implementation Requirements"
    ],
    "key_takeaways": [
      "FDA has approved multiple AI diagnostic tools",
      "Healthcare AI market projected to reach $45B by 2026"
    ]
  },
  "constraints": {
    "voice_profile_id": "yyyyyyyy-...",
    "must_follow_voice": true
  }
}
```

**Post-Request Script:**
```javascript
var json = pm.response.json();
pm.environment.set("brief_id", json.brief_id);
```

---

### 5.2 Force Regenerate Brief

Same as above but add query param:

| Field | Value |
|---|---|
| URL | `{{base_url}}/ideation/ideate?regenerate=true` |

---

### 5.3 Get All Briefs for Brand

`GET /ideation/briefs/{brand_id}`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/ideation/briefs/{{brand_id}}` |
| Query Params | `topic` (optional, case-insensitive filter) |

**Example with filter:**
```
{{base_url}}/ideation/briefs/{{brand_id}}?topic=AI in Healthcare
```

**Expected Response (200):**
```json
{
  "brand_id": "xxxxxxxx-...",
  "count": 2,
  "briefs": [
    { "brief_id": "...", "topic": "AI in Healthcare", "content_brief_json": {...}, ... },
    { "brief_id": "...", "topic": "Cloud Security", "content_brief_json": {...}, ... }
  ]
}
```

---

### 5.4 Get Brief by ID

`GET /ideation/brief/{brief_id}`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/ideation/brief/{{brief_id}}` |

---

### 5.5 Save Brief (Deferred Persistence)

`POST /ideation/save`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/ideation/save` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "brief_id": "{{brief_id}}",
  "brand_id": "{{brand_id}}",
  "voice_profile_id": "{{profile_id}}",
  "topic": "AI in Healthcare",
  "content_brief": {
    "target_audience": "Healthcare administrators evaluating AI adoption",
    "seo_keywords": ["AI diagnostics", "healthcare AI"],
    "h2_outline": ["AI Diagnostic Applications", "Data Privacy"],
    "key_takeaways": ["FDA approved multiple AI tools"]
  },
  "constraints": {
    "voice_profile_id": "{{profile_id}}",
    "must_follow_voice": true
  }
}
```

---

## 6. Agent 3 – Content Execution

### 6.1 Generate Content (Auto-Fetch Mode)

`POST /execute`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/execute` |
| Content-Type | `application/json` |
| Query Params | `save_to_db=true`, `regenerate=false` |

**Body (JSON) — Auto-Fetch (Recommended):**
```json
{
  "brand_id": "{{brand_id}}",
  "platforms": ["blog", "linkedin", "twitter", "email"],
  "execution_mode": "single",
  "execution_version": "v1"
}
```

> **Auto-fetch** uses `brand_id` to pull the latest voice profile and content brief from the DB automatically.

**Expected Response (200):**
```json
{
  "blog": {
    "title": "How AI Transforms Healthcare",
    "content": "## AI Diagnostic Applications\n\nAI marketing uses..."
  },
  "linkedin": {
    "post": "AI is transforming healthcare. Here's how:\n\n1. Saves time\n2. Improves accuracy..."
  },
  "twitter": {
    "thread": [
      "AI is changing healthcare forever. Here's what you need to know 🧵",
      "1/ AI saves clinicians 10+ hours per week on diagnostics",
      "2/ Start your AI journey today. Get a free trial 👇"
    ]
  },
  "email": {
    "subject": "Transform Your Practice with AI",
    "preview": "Discover how AI saves time and improves results",
    "body": "Hi there,\n\nAI is revolutionizing healthcare...",
    "cta": "Start Free Trial"
  }
}
```

---

### 6.2 Generate Content (Manual Mode)

`POST /execute`

**Body (JSON) — Full Manual Input:**
```json
{
  "brand_voice_profile": {
    "tone": {
      "primary": "Professional",
      "secondary": ["Empowering", "Clear"],
      "description": "Professional yet approachable communication"
    },
    "dos": ["Use active voice", "Keep sentences under 20 words"],
    "donts": ["Use jargon", "Write in passive voice"],
    "forbidden_phrases": ["leverage", "synergy"],
    "preferred_vocabulary": ["empower", "transform"]
  },
  "content_brief": {
    "topic": "AI in Marketing",
    "target_audience": "Marketing professionals",
    "key_messages": ["AI saves time", "AI improves accuracy"],
    "keywords": ["AI marketing", "automation"],
    "cta": "Start your free trial",
    "blog_outline": ["What is AI Marketing", "Benefits of AI", "Getting Started"]
  },
  "platforms": ["blog", "linkedin", "twitter", "email"],
  "execution_mode": "single"
}
```

---

### 6.3 Generate with Specific Brief

```json
{
  "brand_id": "{{brand_id}}",
  "brief_id": "{{brief_id}}",
  "platforms": ["blog", "linkedin"],
  "execution_mode": "single",
  "execution_version": "v1"
}
```

---

### 6.4 Multi-Persona Execution (V2)

```json
{
  "brand_id": "{{brand_id}}",
  "platforms": ["blog", "linkedin"],
  "execution_version": "v2",
  "persona_ids": ["persona-uuid-1", "persona-uuid-2"]
}
```

---

### 6.5 Force Regeneration

| Field | Value |
|---|---|
| URL | `{{base_url}}/execute?regenerate=true` |

> Uses higher temperature for varied output.

---

### 6.6 Save Content (Deferred)

`POST /execute/save`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/execute/save` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "brand_id": "{{brand_id}}",
  "voice_profile_id": "{{profile_id}}",
  "content_brief_id": "{{brief_id}}",
  "output_data": {
    "blog": { "title": "...", "content": "..." },
    "linkedin": { "post": "..." }
  },
  "metadata": {
    "execution_version": "v1",
    "generated_at": "2026-02-19T15:00:00Z"
  }
}
```

---

### 6.7 Get Content by Brand

`GET /execute/content/{brand_id}`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/execute/content/{{brand_id}}` |
| Query Params | `execution_version` (optional: `v1`, `v2`), `brief_id` (optional) |

**Examples:**
```
{{base_url}}/execute/content/{{brand_id}}
{{base_url}}/execute/content/{{brand_id}}?execution_version=v1
{{base_url}}/execute/content/{{brand_id}}?brief_id={{brief_id}}
```

---

## 7. Pipeline Orchestration

> The Pipeline API provides a **stateful, server-enforced workflow** that chains Agent 1 → Agent 2 → Agent 3 in order.

### 7.1 Start Pipeline

`POST /pipeline/start`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/pipeline/start?brand_id={{brand_id}}&mode=v1` |

**Expected Response (200):**
```json
{
  "pipeline_id": "pipe-xxxxxxxx-...",
  "brand_id": "xxxxxxxx-...",
  "trace_id": "trace-...",
  "mode": "v1",
  "status": "IDLE",
  "created_at": "2026-02-19T15:00:00Z",
  "updated_at": "2026-02-19T15:00:00Z",
  "voice_profile_id": null,
  "brief_id": null,
  "execution_id": null,
  "steps": {
    "voice_profiling": "PENDING",
    "ideation": "PENDING",
    "execution": "PENDING"
  },
  "metadata": {},
  "error": null
}
```

**Post-Request Script:**
```javascript
var json = pm.response.json();
pm.environment.set("pipeline_id", json.pipeline_id);
```

---

### 7.2 Get Pipeline State

`GET /pipeline/{pipeline_id}/state`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/pipeline/{{pipeline_id}}/state` |

---

### 7.3 Run Pipeline Step

`POST /pipeline/{pipeline_id}/step/{step_name}`

**Step Names:** `voice_profiling`, `ideation`, `execution`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/pipeline/{{pipeline_id}}/step/voice_profiling` |
| Content-Type | `application/json` |

**Body for `voice_profiling` step:**
```json
{
  "input_type": "text",
  "input_value": "Our company focuses on cutting-edge AI solutions with a professional, data-driven tone."
}
```

**Body for `ideation` step:**
```json
{
  "topic": "AI in Healthcare",
  "market": "Healthcare"
}
```

**Body for `execution` step:**
```json
{
  "platforms": ["blog", "linkedin", "twitter", "email"]
}
```

---

### 7.4 Approve Step Artifact

`POST /pipeline/{pipeline_id}/approve/{step_name}`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/pipeline/{{pipeline_id}}/approve/voice_profiling` |
| Content-Type | `application/json` |

**Body (optional):**
```json
{
  "feedback": "Looks good, approved."
}
```

---

### 7.5 Reject Step Artifact

`POST /pipeline/{pipeline_id}/reject/{step_name}`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/pipeline/{{pipeline_id}}/reject/voice_profiling` |

**Body (optional):**
```json
{
  "feedback": "Tone is too casual."
}
```

---

### 7.6 Regenerate Profile

`POST /pipeline/regenerate/{incoming_id}`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/pipeline/regenerate/{{profile_id}}` |

> Accepts either a `profile_id` or `brand_id`. Generates a new version of the voice profile.

---

## 8. Voice Profile Management

### 8.1 Submit Voice Feedback (Accept/Reject)

`POST /voice/{brand_id}/feedback`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/voice/{{brand_id}}/feedback` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "accepted": true
}
```

---

### 8.2 Update Voice Rules

`PATCH /voice/{brand_id}/rules`

| Field | Value |
|---|---|
| Method | `PATCH` |
| URL | `{{base_url}}/voice/{{brand_id}}/rules` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "tone": {
    "primary": "Professional",
    "secondary": ["Friendly", "Clear"],
    "description": "Direct and empathetic communication"
  },
  "dos": [
    "Use active voice",
    "Lead with data",
    "Be empathetic"
  ],
  "donts": [
    "Avoid jargon",
    "No exclamation marks",
    "Don't use passive voice"
  ]
}
```

> **Note:** This creates a **NEW version** of the profile with `DRAFT` status.

---

### 8.3 List Personas (V2)

`GET /voice/{brand_id}/personas`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/voice/{{brand_id}}/personas` |

**Expected Response (200):**
```json
{
  "status": "success",
  "brand_id": "xxxxxxxx-...",
  "count": 2,
  "personas": [...]
}
```

---

### 8.4 Refine Profile (V1 → V2)

`POST /profiles/{profile_id}/refine`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/profiles/{{profile_id}}/refine` |

> Runs V2 dimensional analysis on a V1 profile. Returns `dimensional_scores` and `implicit_rules`.

**Expected Response (200):**
```json
{
  "status": "success",
  "profile_id": "yyyyyyyy-...",
  "refinement": {
    "dimensional_scores": {
      "humor": 0.15,
      "empathy": 0.65,
      "authority": 0.80,
      "formality": 0.75,
      "urgency": 0.30
    },
    "implicit_rules": [...]
  }
}
```

---

## 9. Feedback Loop

### 9.1 Submit Profile Feedback (Accept/Reject/Rewrite)

`POST /profiles/{profile_id}/feedback`

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `{{base_url}}/profiles/{{profile_id}}/feedback` |
| Content-Type | `application/json` |

**Body (JSON):**
```json
{
  "action": "accept"
}
```

> **Valid actions:** `accept`, `reject`, `rewrite`

**Expected Response (200):**
```json
{
  "profile_id": "yyyyyyyy-...",
  "action": "accept",
  "acceptance_rate": 0.75,
  "rewrite_count": 1,
  "total_feedback_events": 4
}
```

---

### 9.2 Get Profile Stats

`GET /profiles/{profile_id}/stats`

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `{{base_url}}/profiles/{{profile_id}}/stats` |

**Expected Response (200):**
```json
{
  "profile_id": "yyyyyyyy-...",
  "acceptance_rate": 0.75,
  "rewrite_count": 1,
  "total_feedback_events": 4
}
```

---

## 10. End-to-End Test Flow

Follow these steps **in order** to test the full pipeline manually:

### 🟢 Happy Path

```
Step 1 ─ POST /brands/create              → Save {{brand_id}}
Step 2 ─ POST /ingest (text payload)       → Save {{brand_id}}, {{profile_id}}
Step 3 ─ GET  /ingest/profile/{{profile_id}} → Verify profile data
Step 4 ─ POST /ingest/approve/{{profile_id}} → DRAFT → APPROVED
Step 5 ─ POST /ideation/ideate             → Save {{brief_id}}
Step 6 ─ GET  /ideation/brief/{{brief_id}}  → Verify brief data
Step 7 ─ POST /execute (auto-fetch)        → Get generated content
Step 8 ─ GET  /execute/content/{{brand_id}} → Verify saved content
```

### 🔄 Feedback Loop Test

```
Step 1 ─ POST /profiles/{{profile_id}}/feedback   { "action": "reject" }
Step 2 ─ POST /pipeline/regenerate/{{profile_id}}  → New profile version
Step 3 ─ POST /profiles/{{NEW_profile_id}}/feedback { "action": "accept" }
Step 4 ─ GET  /profiles/{{NEW_profile_id}}/stats    → Verify metrics
```

### 🔁 Pipeline Orchestration Test

```
Step 1 ─ POST /pipeline/start?brand_id={{brand_id}}
Step 2 ─ POST /pipeline/{{pipeline_id}}/step/voice_profiling  (text payload)
Step 3 ─ GET  /pipeline/{{pipeline_id}}/state                  (check: voice_profiling=COMPLETED)
Step 4 ─ POST /pipeline/{{pipeline_id}}/approve/voice_profiling
Step 5 ─ POST /pipeline/{{pipeline_id}}/step/ideation          (topic payload)
Step 6 ─ POST /pipeline/{{pipeline_id}}/approve/ideation
Step 7 ─ POST /pipeline/{{pipeline_id}}/step/execution         (platforms payload)
Step 8 ─ GET  /pipeline/{{pipeline_id}}/state                  (check: status=COMPLETED)
```

---

## Error Reference

| HTTP Code | Meaning | When |
|---|---|---|
| 200 | Success | Normal operation |
| 400 | Bad Input | Missing required fields |
| 404 | Not Found | Brand/Profile/Brief does not exist |
| 422 | Validation Error | Pydantic schema mismatch |
| 500 | Internal Error | Agent failure / DB error |

**Error Response Shape:**
```json
{
  "detail": "Error message description"
}
```

**Validation Error Shape (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "brand_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Quick Checklist

- [ ] Server running at `{{base_url}}`
- [ ] MySQL/DB running and accessible
- [ ] `.env.local` environment variables loaded
- [ ] `GOOGLE_API_KEY` is valid (needed for LLM calls)
- [ ] `TAVILY_API_KEY` is valid (needed for Agent 2 web research)
- [ ] Brand created and `brand_id` saved in Postman env
- [ ] Voice profile generated and `profile_id` saved
- [ ] Content brief generated and `brief_id` saved
