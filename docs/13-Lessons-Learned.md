# Lessons Learned

## 1. Small, Specialized Agents Beat Generalists
Initially, we tried to build one massive prompt to do everything. It failed constantly—it would forget negative constraints or hallucinate fake SEO data.
**Lesson:** The "Meta-Agent" architecture (chaining multiple specialized agents) is the only way to build reliable AI pipelines. Agent 1 *only* cares about tone. Agent 2 *only* cares about facts. Agent 3 *only* cares about writing. This modularity made debugging infinitely easier.

## 2. API Contracts Must Be Treated Like Concrete
When building an AI service that another team will consume (via MCP), the unstructured nature of LLMs is a massive liability.
**Lesson:** Never pass raw LLM output directly to a client. Every output from our agents is forced through a strict Pydantic model. If the LLM hallucinates an invalid JSON structure, the internal system catches it and retries, ensuring the external Platform Team *always* receives the exact JSON schema defined in our OpenAPI spec.

## 3. Human-in-the-Loop is Mandatory for Voice
We initially designed the pipeline to run end-to-end automatically. However, users were frustrated when Agent 1 misidentified their tone (e.g., misinterpreting sarcasm as anger), which corrupted the entire downstream output.
**Lesson:** We introduced the `approve` endpoints (e.g., `/pipeline/{id}/approve/voice_profiling`). By pausing the state machine and forcing the human to review and tweak the Voice Profile before moving to Ideation, we increased overall user satisfaction and significantly reduced the number of generated copy rejections.
