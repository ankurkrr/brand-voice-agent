# Testing Strategy

Because LLM outputs are inherently non-deterministic, traditional unit testing is insufficient. We employ a hybrid testing strategy combining deterministic API contracts and semantic LLM evaluations.

## 1. Deterministic Unit Testing

We use `pytest` to validate the core infrastructure, ignoring the LLM calls.
- **Pydantic Validation (`debug_pydantic.py`):** Ensures that if the LLM hallucinates a malformed JSON profile, the FastAPI layer catches it and returns a strict 422 error, rather than crashing the database.
- **Database Operations (`quick_db_test.py`):** Tests CRUD operations on the MySQL database, ensuring foreign key constraints (e.g., deleting a Brand cascades to delete its Voice Profiles).

## 2. Integration Testing & Postman

We maintain a massive Postman collection (`postman_collection_generated.json`, ~270KB) that serves as our primary integration suite.
- Simulates the exact MCP Handoff flow (Start Pipeline ➔ Profile ➔ Ideate ➔ Execute).
- Validates HTTP status codes and response schemas at every step.

## 3. "Self-Reflective" LLM Testing (LangSmith)

To test the *quality* of the generated copy, we use LangSmith to run automated evaluations against a golden dataset.
1. We provide Agent 3 with a specific Voice Profile (e.g., "Sarcastic and Short").
2. Agent 3 generates a Twitter post.
3. An independent "Evaluator LLM" analyzes the output and scores it out of 10 for tone adherence.
4. If a prompt tweak causes the average tone score to drop below 8.0, the CI build fails.
