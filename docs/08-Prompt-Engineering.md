# Prompt Engineering

The Meta-Agent's success relies entirely on complex, chained prompt engineering utilizing Google's Gemini 2.5 Flash via LangChain.

## 1. Agent 1: The Rule Extractor
Agent 1's prompt is designed to act as a strict linguistic analyst. It forces the LLM to output a precise JSON schema using LangChain's `StructuredOutputParser`.

**Key Prompt Directives:**
> "You are an elite brand strategist and linguist. Analyze the following source text.
> 1. Extract 3-5 high-level 'Tone Descriptors'.
> 2. Identify explicit 'Banned Words' (words the brand actively avoids).
> 3. Extract 'Implicit Rules' (e.g., 'Sentences are short and punchy', or 'Heavy use of emojis').
> 4. Calculate 'Dimensional Scores' on a 1-10 scale (e.g., Formal vs. Casual)."

## 2. Agent 3: The Multi-Channel Executor
Agent 3 utilizes **Retrieval-Augmented Prompting**. The prompt is dynamically assembled at runtime by combining data from MySQL and ChromaDB.

**Prompt Assembly:**
```text
SYSTEM:
You are an expert copywriter for brand: {brand_name}.
You must strictly adhere to the following Voice Profile:
{voice_profile_json}

CRITICAL: NEVER use these banned words: {banned_words_list}

Here are examples of how the brand sounds (retrieved from ChromaDB):
{few_shot_examples}

USER:
Using the strategic constraints below, write a {platform_type} post:
{content_brief_json}

Platform Constraints for {platform_type}:
- Max Length: {max_chars}
- Formatting: {formatting_rules}
```

## 3. The Self-Reflection Loop
Because LLMs sometimes ignore negative constraints (e.g., using a banned word anyway), Agent 3 includes a programmatic validation step.
1. Output is generated.
2. Python iterates over the `banned_words_list` against the output string.
3. If a match is found, the system automatically triggers a "Rewrite Prompt":
   > "Your previous draft violated the brand guidelines by using the word '{banned_word}'. Rewrite the text completely to remove it."
