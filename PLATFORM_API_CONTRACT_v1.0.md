# Platform API Contract v1.0 (Frozen)

**Status:** RELEASED
**Version:** 1.0.0
**Enforcement:** Strict

This document defines the **Canonical Data Contracts** for the Multi-Agent AI Backend.
Platform web integrations **MUST** adhere to these schemas.

---

## 0. Brand Creation

**Endpoint:** `POST /brands/create`

> **Platform Integration:** Pass your `org_id` as the `brand_id` field. It will be used as-is throughout all agents. If omitted, a UUID is auto-generated.

---

## 1. Agent 1: Voice Profile

**Endpoint:** `POST /ingest` / `GET /profile/{id}`

### Schema
```typescript
interface VoiceProfile {
  // META
  id: string;              // UUID
  brand_id: string;        // UUID
  version: "v1" | "v2";    // Logic Branching Key
  status: "DRAFT" | "APPROVED";
  
  // CORE IDENTITY (Required)
  tone: {
    primary: string;       // e.g. "Professional"
    secondary: string[];   // e.g. ["Friendly", "Concise"] (May be empty)
    description: string;   // Full tone summary
  };

  // RULES (Required)
  rules: {
    dos: string[];              // e.g. "Use active voice"
    donts: string[];            // e.g. "No jargon"
    forbidden_phrases: string[]; // e.g. "Synergy"
    preferred_vocabulary: string[]; // (May be empty)
  };

  // METRICS (Version Dependent)
  // v1: Always NULL
  // v2: Object or NULL (if analysis failed)
  dimensional_scores: {
    humor: number;         // 0.0 - 1.0
    empathy: number;       // 0.0 - 1.0
    authority: number;     // 0.0 - 1.0
    formality: number;     // 0.0 - 1.0
    urgency: number;       // 0.0 - 1.0
  } | null;

  // READ-ONLY
  style_metrics: {
    avg_sentence_length?: number;
    reading_level?: string;
  };
}
```

### Platform Behavior Rules
1.  **Version Checking:** Branch UI logic on `version`.
    *   If `v1`: Do NOT attempt to render Radar Chart.
    *   If `v2`: Check `dimensional_scores !== null` before rendering.
2.  **Fallback:** If `tone.secondary` is empty, hide the secondary tone badge/section.

---

## 2. Agent 2: Content Brief

**Endpoint:** `POST /ideation/ideate`

### Schema
```typescript
interface ContentBriefResponse {
  brief_id: string;        // UUID
  topic: string;           // Echoed back
  status: "generated";
  
  // STRATEGY (Required)
  content_brief: {
    target_audience: string;
    key_takeaways: string[]; // List of key messages
    seo_keywords: string[];  // List of keywords
    h2_outline: string[];    // Blog post structure
    cta: string;             // Call to Action
  };
  
  // LINEAGE (Required)
  constraints: {
    voice_profile_id: string;
    must_follow_voice: boolean;
  };
}
```

### Platform Behavior Rules
1.  **Idempotency:** This endpoint is pure. Repeated calls with the same topic/brand return the same cached brief (via fingerprinting).
2.  **Rendering:** All fields in `content_brief` are guaranteed to exist, but lists/strings *may* be empty if the AI found no data.

---

## 3. Agent 3: Platform Execution

**Endpoint:** `POST /execute`

### Schema
```typescript
interface ExecutionResponse {
  id?: string;             // Generation UUID
  
  // PLATFORM CONTENT (Optional Keys)
  // Only requested platforms will be present.
  
  blog?: {
    title: string;
    body: string;          // Markdown formatted
    meta_description?: string;
  };

  linkedin?: {
    text: string;          // Plain text with hashtags
  };

  twitter?: {
    thread: string[];      // Array of tweet strings. 
    // platform must render as threaded UI.
  };

  email?: {
    subject: string;
    body: string;          // HTML or Text
  };

  // DEBUG & AUDIT
  raw_json: object;        // Complete unparsed LLM output
}
```

### Platform Behavior Rules
1.  **Access Safety:** NEVER access platform keys directly without checking existence.
    *   ✅ Safe: `response.twitter?.thread`
    *   ❌ Unsafe: `response.twitter.thread`
2.  **Markdown:** The `blog.body` is Markdown. The platform MUST render it (H1, H2, bullets).
3.  **Thread Rendering:** `twitter.thread` is an array. Render as connected cards.

---

## Global Error Contract

**HTTP 4xx / 5xx Responses**
```json
{
  "detail": "Error message description"
}
```
*   **400:** Bad Input (missing required fields).
*   **404:** Brand/Profile not found.
*   **500:** Internal Error (Retry safe? No, unless 503).
