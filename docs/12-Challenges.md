# Challenges & Solutions

## 1. The "Bland AI" Problem

**Challenge:** Even when provided with a list of "Tone Descriptors" (e.g., "Professional, Authoritative"), the LLM often reverted to its default, highly recognizable AI tone (e.g., "In today's fast-paced digital world...").

**Solution (The RAG-Style Injection):** We realized that explicit rules are not enough to capture stylistic nuance. We implemented ChromaDB to vectorize the original brand documents. By retrieving the exact phrasing of the brand's original text and injecting it into Agent 3's prompt as a Few-Shot example, the LLM was forced to mimic the specific cadence and sentence structure of the brand, drastically improving output quality.

## 2. Handling State in a Stateless REST API

**Challenge:** The external Platform Team needed to integrate our agents via the Model Context Protocol (MCP). However, our agents require a specific sequence (You cannot write the copy before extracting the voice). HTTP REST is naturally stateless, leading to race conditions where the MCP server might trigger Agent 3 too early.

**Solution (The Pipeline State Machine):** We implemented a strict Pipeline Controller backed by MySQL. Every request must reference a `pipeline_id`. If the MCP server calls `POST /pipeline/{id}/step/execution` but the database shows that `step/voice_profiling` is still `PENDING`, the FastAPI router immediately returns a `400 Bad Request: Prerequisites not met`.

## 3. Evolving Schemas and Null Safety

**Challenge:** As the product evolved, we added `dimensional_scores` to the Voice Profile to render radar charts in the frontend. This created a breaking change for older profiles stored in the database.

**Solution:** We introduced explicit `version` tags (`v1`, `v2`) in the MySQL `voice_profiles` table. We updated the Pydantic models to make `dimensional_scores` an `Optional[Dict]`. We clearly documented this requirement in the `PLATFORM_API_CONTRACT_v1.0.md` and `mcp_handoff_guide.md`, warning the platform team to implement null-checking on the frontend to prevent React crashes when rendering legacy v1 profiles.
