import logging
import uuid
from typing import Dict, Any, Optional

from domain.models.token_usage import TokenUsage
from data.repos.token_usage_repo import TokenUsageRepo

logger = logging.getLogger(__name__)

# Basic pricing per 1000 tokens (Prompt, Completion)
# Note: Google Gemini model prices are approximated based on std rates.
PRICING = {
    "openai:gpt-4o": (0.005, 0.015),
    "openai:gpt-4o-mini": (0.00015, 0.0006),
    "openai:text-embedding-3-small": (0.00002, 0.0),
    "google:gemini-1.5-pro": (0.00125, 0.00375),
    "google:gemini-1.5-flash": (0.000075, 0.0003),
    "tavily:search": (5.0, 0.0), # Assuming $5.00 per 1000 requests for standard API
}

class TokenTracker:
    def __init__(self, repo: Optional[TokenUsageRepo] = None):
        self.repo = repo or TokenUsageRepo

    def calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        import os
        key = f"{provider}:{model}".lower()
        
        # Standardize ENV key lookup
        # e.g., 'gemini', 'models/gemini-2.5-flash' -> GEMINI_MODELS_GEMINI_2_5_FLASH
        clean_model = model.replace(".", "_").replace("-", "_").replace("/", "_").upper()
        clean_provider = provider.upper()
        env_prefix = f"{clean_provider}_{clean_model}"
        
        env_prompt_key = f"{env_prefix}_PRICE_PROMPT"
        env_comp_key = f"{env_prefix}_PRICE_COMPLETION"
        
        env_prompt_cost = os.getenv(env_prompt_key)
        env_comp_cost = os.getenv(env_comp_key)
        
        if env_prompt_cost is not None and env_comp_cost is not None:
            try:
                prompt_pricing = float(env_prompt_cost)
                completion_pricing = float(env_comp_cost)
            except ValueError:
                prompt_pricing, completion_pricing = PRICING.get(key, (0.0, 0.0))
        else:
            # Fallback to Hardcoded PRICING Dictionary
            prompt_pricing, completion_pricing = PRICING.get(key, (0.0, 0.0))
            
            # Substring heuristic fallback if exact key missing
            if prompt_pricing == 0.0 and completion_pricing == 0.0:
                if "thinking" in key or "reasoning" in key:
                    prompt_pricing, completion_pricing = (0.0003, 0.0025)
                elif "pro" in key:
                    prompt_pricing, completion_pricing = (0.00125, 0.00375)
                elif "flash" in key:
                    prompt_pricing, completion_pricing = (0.000075, 0.0003)
                    
        cost = (prompt_tokens / 1000.0 * prompt_pricing) + (completion_tokens / 1000.0 * completion_pricing)
        return cost

    async def _safe_save(self, record: TokenUsage) -> None:
        try:
            await self.repo.save(record)
        except Exception as e:
            logger.error(f"Failed to track tokens: {str(e)}")

    async def track_llm_usage(
        self,
        pipeline_id: Optional[str],
        request_id: str,
        agent_name: str,
        provider: str,
        model: str,
        usage: Optional[Any] = None,
        response: Optional[Any] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track LLM completion usage."""
        try:
            pipeline_id = pipeline_id or "unknown_pipeline"
            prompt_tokens, completion_tokens, total_tokens = 0, 0, 0

            # If a response object from LangChain is passed instead of raw usage
            if response is not None and usage is None:
                if hasattr(response, "usage_metadata") and isinstance(response.usage_metadata, dict):
                    usage = response.usage_metadata
                elif hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
                    usage = response.response_metadata.get("token_usage", {})

            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
                completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            elif usage is not None:
                prompt_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                completion_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)

            cost = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)

            record = TokenUsage(
                request_id=request_id,
                pipeline_id=pipeline_id,
                agent_name=agent_name,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                metadata=metadata or {}
            )
            await self._safe_save(record)
        except Exception as e:
            logger.error(f"TokenTracker track_llm_usage error: {str(e)}")

    async def track_embedding_usage(
        self,
        pipeline_id: Optional[str],
        request_id: str,
        agent_name: str,
        provider: str,
        model: str,
        tokens: int,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track Embedding usage."""
        try:
            pipeline_id = pipeline_id or "unknown_pipeline"
            cost = self.calculate_cost(provider, model, tokens, 0)
            
            record = TokenUsage(
                request_id=request_id,
                pipeline_id=pipeline_id,
                agent_name=agent_name,
                provider=provider,
                model=model,
                prompt_tokens=tokens,
                completion_tokens=0,
                total_tokens=tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                metadata=metadata or {}
            )
            await self._safe_save(record)
        except Exception as e:
            logger.error(f"TokenTracker track_embedding_usage error: {str(e)}")

    async def track_tavily_usage(
        self,
        pipeline_id: Optional[str],
        request_id: str,
        agent_name: str,
        usage: Optional[Any],
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track Tavily Search API usage."""
        try:
            pipeline_id = pipeline_id or "unknown_pipeline"
            if not metadata:
                metadata = {}
                
            prompt_tokens = 0
            if isinstance(usage, dict) and "tokens" in usage:
                # Some API returns might encode usage tokens instead of "1 request"
                prompt_tokens = usage.get("tokens", 1)
            else:
                prompt_tokens = 1
                metadata["request"] = 1
            
            cost = self.calculate_cost("tavily", "search", prompt_tokens, 0)

            record = TokenUsage(
                request_id=request_id,
                pipeline_id=pipeline_id,
                agent_name=agent_name,
                provider="tavily",
                model="search",
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=prompt_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                metadata=metadata
            )
            await self._safe_save(record)
        except Exception as e:
            logger.error(f"TokenTracker track_tavily_usage error: {str(e)}")
