# Performance & Optimization

## 1. Model Selection (Cost vs. Speed)

*Initial Architecture:* We utilized `gpt-4o` for all three agents.
*Result:* Exorbitant API costs and extremely slow generation times (sometimes >60 seconds for Agent 3), leading to HTTP timeouts on the MCP Server.

*Optimization:* We migrated the entire stack to **Google Gemini 2.5 Flash**.
- **Agent 1 (Profiling):** Dropped from 35s to 12s.
- **Agent 3 (Execution):** Dropped from 60s to 18s.
- **Cost:** Reduced by over 80% (Tracked in `Token_Cost_Analysis.csv`).

## 2. Asynchronous Execution

Agent 3 generates copy for four platforms simultaneously (Blog, LinkedIn, Twitter, Email).
Initially, this was done synchronously in a Python `for` loop, causing latency to stack (e.g., 5s + 4s + 3s + 6s = 18s).
By rewriting the LangChain execution step to use `asyncio.gather()`, we execute all four LLM chains in parallel. Total execution time is now bounded by the slowest platform (usually the Blog post, ~6 seconds).

## 3. Deduplication Caching

Agent 2 relies on the Tavily API, which charges per search. If multiple users ask the agent to research "AI in Healthcare", doing a live web search every time is wasteful.
We implemented a fingerprint-based cache in MySQL. If the requested `topic` and `market` match an existing `content_brief` within the last 7 days, the system returns the cached brief instantly, bypassing Tavily and the LLM entirely.
