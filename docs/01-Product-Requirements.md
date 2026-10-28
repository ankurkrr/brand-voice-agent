# Product Requirements Document (PRD)

## 1. Executive Summary
The **Brand Voice Meta-Agent** is a sophisticated, 3-stage AI orchestration system designed to automate marketing content creation without sacrificing brand authenticity. It acts as an autonomous marketing department by ingesting brand assets to learn a specific "Voice," researching industry topics, and executing platform-native copy across multiple channels (LinkedIn, Twitter, Blog, Email).

## 2. Problem Statement
- **Generic AI Output:** Most LLM-generated marketing content sounds robotic, generic, and lacks the specific tone, stylistic nuances, and vocabulary of a company's established brand voice.
- **Fragmented Workflows:** Marketing teams use disjointed tools for brand rule management, SEO research, and copy drafting.
- **Platform Inconsistency:** A brand's voice often gets diluted when translated across different platforms (e.g., a Twitter thread requires different pacing than a Newsletter, but must maintain the same brand persona).

## 3. Solution Overview
We engineered a linear "Meta-Agent" pipeline comprising three specialized, heavily constrained agents:
1. **Agent 1 (Brand Voice Profiler):** Analyzes PDFs and URLs to build a deterministic, reusable "Golden Record" of a brand's voice.
2. **Agent 2 (Content Strategist):** Researches topics via the Tavily API to generate data-backed strategic content briefs (SEO, audience targeting).
3. **Agent 3 (Multi-Channel Executor):** Fuses the Voice Profile and the Content Brief to generate validated, platform-native copy.

## 4. User Journeys

### Journey 1: Brand Ingestion (The Setup)
1. User uploads a brand guidelines PDF or provides a URL to their best blog post.
2. Agent 1 extracts the tone, grammatical rules, banned words, and stylistic examples.
3. The system saves a `v2` Voice Profile to the MySQL database, generating a "Dimensional Score" radar chart for visual feedback.

### Journey 2: Orchestrated Content Generation (The Execution)
1. An external platform (via MCP) or a local user submits a topic (e.g., "AI in Healthcare").
2. The Pipeline Controller triggers Agent 2 to research the web and build an SEO brief.
3. Upon approval, the Pipeline Controller triggers Agent 3, requesting outputs for Twitter, LinkedIn, and Email.
4. Agent 3 generates the copy, validates it against the banned words list from Agent 1, and returns the final artifacts.

## 5. Functional Requirements
- **F1 - Strict Voice Adherence:** Generated content MUST pass an automated validation step verifying that stylistic rules from the Voice Profile are applied.
- **F2 - Pipeline State Management:** The system MUST track the state of the 3-step pipeline (`IDLE` ➔ `IN_PROGRESS` ➔ `COMPLETED`) via a centralized REST API.
- **F3 - Model Context Protocol (MCP) Handoff:** The backend MUST expose a stateless REST interface designed specifically to be wrapped by an external MCP server, allowing `org_id` to map directly to `brand_id`.
- **F4 - Web Research:** Agent 2 MUST utilize an external search API (Tavily) to ground its content briefs in factual, up-to-date data.

## 6. Key Performance Indicators (KPIs)
| Metric | Target |
| :--- | :--- |
| **Voice Profile Generation Time** | 10-30 seconds |
| **Content Execution Time** | 15-45 seconds (across 4 platforms) |
| **Brand Rule Compliance Rate** | > 95% (Automated validation) |
| **Pipeline Reliability** | 99.9% uptime for HTTP `/pipeline/step` |
