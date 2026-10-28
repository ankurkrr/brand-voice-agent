# API Contracts (v1.0 Frozen)

**Status:** FROZEN
**Enforcement:** Strict Schema Validation

This document is the **Single Source of Truth** for all public API endpoints.
Backend changes that violate this contract are strictly forbidden.

---

## 1. Ingestion (Voice Profile)

**Endpoint:** `POST /ingest`
**Content-Type:** `multipart/form-data` (Files) OR `application/json` (Text/URL)

### Request (Multipart)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | File | Yes | PDF, DOCX, TXT |
| `brand_id` | UUID | No | If updating existing brand |

### Response (`VoiceProfile`)
```json
{
  "brand_id": "uuid-string",
  "version": "v1" | "v2",
  "tone": {
    "primary": "string",
    "secondary": ["string"] | [],
    "description": "string"
  },
  "rules": {
    "dos": ["string"],
    "donts": ["string"]
  },
  "best_match_examples": [
    {
      "example_id": "string",
      "text": "string"
    }
  ],
  "dimensional_scores": {  // MAY BE NULL
    "humor": 0.5,
    "empathy": 0.7,
    "authority": 0.2,
    "formality": 0.8,
    "urgency": 0.1
  } | null
}
```

---

## 2. Ideation (Content Brief)

**Endpoint:** `POST /ideation/ideate`
**Content-Type:** `application/json`

### Request
```json
{
  "brand_id": "uuid-string",  // Required
  "topic": "string",          // Required
  "market": "string",         // Optional
  "region": "string"          // Optional
}
```

### Response (`ContentBrief`)
```json
{
  "brief_id": "uuid-string",
  "status": "generated",
  "content_brief": {
    "target_audience": "string",
    "key_takeaways": ["string"],
    "seo_keywords": ["string"] | [],
    "h2_outline": ["string"],
    "cta": "string"
  }
}
```

---

## 3. Execution (Content Generation)

**Endpoint:** `POST /execute`
**Content-Type:** `application/json`

### Request
```json
{
  "brand_id": "uuid-string",
  "brief_id": "uuid-string",  // Optional (system finds latest)
  "platforms": ["twitter", "linkedin", "blog"] // Required
}
```

### Response (`ExecutionResponse`)
**Warning:** Platform keys exist ONLY if requested. Guard access!

```json
{
  "id": "uuid-string",
  "blog": {              // Optional
    "title": "string",
    "content": "markdown-string"
  },
  "linkedin": {          // Optional
    "post": "string"
  },
  "twitter": {           // Optional
    "thread": ["string"] 
  },
  "email": {             // Optional
    "subject": "string",
    "preview": "string",
    "body": "string",
    "cta": "string"
  },
  "raw_json": {}         // Debug dump (Always present)
}
```

---

## 4. Updates & Feedback

### Update Rules
**Endpoint:** `PATCH /voice/{brand_id}/rules`
**Request:**
```json
{
  "tone": {"primary": "string", ...},
  "dos": ["string"],
  "donts": ["string"]
}
```

### Submit Feedback
**Endpoint:** `POST /profiles/{profile_id}/feedback`
**Request:**
```json
{
  "action": "accept" | "reject" | "rewrite"
}
```
**Response:**
```json
{
  "acceptance_rate": 0.75,
  "rewrite_count": 3
}
```
