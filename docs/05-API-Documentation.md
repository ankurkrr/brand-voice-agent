# API Documentation (MCP Handoff)

The Voice Meta-Agent exposes a robust REST API specifically designed to be wrapped by an external Model Context Protocol (MCP) server. The design allows external platforms to pass their native `org_id` directly to our system as the `brand_id`.

## 1. Core State Machine Endpoints

### POST `/pipeline/start`
Initializes a new pipeline state machine for a specific brand.
- **Query Parameter:** `brand_id=your_org_id`
- **Response:** `{ "pipeline_id": "uuid-1234", "state": "IDLE" }`

### POST `/pipeline/{id}/step/voice_profiling`
Triggers Agent 1. This is a synchronous, blocking call (10-30s).
- **Body:** `{ "input_type": "url", "input_value": "https://brand.com/blog" }`
- **Response:** The generated Voice Profile JSON.

### POST `/pipeline/{id}/approve/voice_profiling`
Advances the state machine, confirming human approval of the voice profile.
- **Body:** `{ "feedback": "optional string" }`

### POST `/pipeline/{id}/step/ideation`
Triggers Agent 2. This is a synchronous, blocking call (5-15s).
- **Body:** `{ "topic": "AI in Healthcare", "market": "B2B SaaS" }`
- **Response:** The generated Content Brief JSON.

### POST `/pipeline/{id}/step/execution`
Triggers Agent 3. Generates the final copy (15-45s).
- **Body:** `{ "platforms": ["blog", "linkedin", "twitter", "email"] }`
- **Response:** Array of platform-native text blocks.

### GET `/pipeline/{id}/state`
Retrieves the full aggregate state of the pipeline, returning all associated artifact IDs.

## 2. MCP Integration Strategy
The platform team building the MCP server maps our REST endpoints to MCP tools:
- `start_pipeline` ➔ `POST /pipeline/start`
- `run_voice_profiling` ➔ `POST /pipeline/{id}/step/voice_profiling`
- `run_ideation` ➔ `POST /pipeline/{id}/step/ideation`
- `run_execution` ➔ `POST /pipeline/{id}/step/execution`

## 3. Error Handling Contract
All HTTP error responses follow a strict schema:
```json
{
  "detail": "Human-readable error message."
}
```
- `400`: Bad input (e.g., trying to run Agent 3 before Agent 1 is approved).
- `404`: Pipeline or Brand ID not found.
- `422`: Pydantic validation error.
