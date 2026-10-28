# API Overview & Agent Flow

**Status:** RELEASED (v1.0)
**Audience:** Platform Engineering, Frontend, Mobile

This document outlines the high-level architecture of the Multi-Agent AI Backend.
Use this to understand how data flows between agents and how to orchestrate the pipeline.

---

## 🏗 System Architecture

The backend consists of **3 Autonomous Agents** arranged in a linear pipeline.
Each agent produces a specific artifact that becomes input for the next agent.

### 1. Agent 1: The Voice Profiler
*   **Role:** Ingests brand assets (PDFs, URLs) and extracts the "Brand Voice".
*   **Input:** Files, Text, URLs.
*   **Output:** `VoiceProfile` (Tone, Rules, Examples).
*   **Endpoint:** `POST /ingest`

### 2. Agent 2: The Strategist
*   **Role:** Researches a topic and creates a strategic content brief.
*   **Input:** Topic, Brand ID.
*   **Output:** `ContentBrief` (Audience, Keywords, Outline).
*   **Constraint:** Strictly forbidden from seeing "Voice" data (pure strategy).
*   **Endpoint:** `POST /ideation/ideate`

### 3. Agent 3: The Executor
*   **Role:** Generates platform-native copy using Voice + Strategy.
*   **Input:** Voice Profile ID + Content Brief ID.
*   **Output:** `ExecutionResponse` (Blog, LinkedIn, Twitter, Email).
*   **Endpoint:** `POST /execute`

---

## 🔄 The Orchestration Flow

Platform teams should follow this happy-path sequence:

1.  **Ingest:** Upload brand assets -> Get `brand_id`.
2.  **Ideate:** Send `brand_id` + `topic` -> Get `brief_id`.
3.  **Approve (Optional):** UI can optionally gate here.
4.  **Execute:** Send `brand_id` + `brief_id` -> Get Content.

---

## 🛡 Integration Guarantees

*   **Idempotency:** `POST /ideation/ideate` is idempotent (caches results by topic fingerprint).
*   **Statelessness:** Agents allow "Manual Hydration" (passing full JSON) or "Auto-Fetch" (passing IDs).
    *   *Recommendation:* Use Auto-Fetch (IDs) for consistency.
*   **Null Safety:** The API guarantees **contract stability**, not **data completeness**.
    *   *Rule:* Always check for `null` values before rendering charts.
