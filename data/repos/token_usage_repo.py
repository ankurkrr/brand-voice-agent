import json
import logging
from typing import List, Dict, Any

from domain.models.token_usage import TokenUsage
from data.db.session import get_pool

logger = logging.getLogger(__name__)

class TokenUsageRepo:
    @staticmethod
    async def save(record: TokenUsage) -> None:
        query = """
        INSERT INTO token_usage_logs (
            request_id, pipeline_id, agent_name, provider, model,
            prompt_tokens, completion_tokens, total_tokens,
            cost_usd, latency_ms, metadata, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (pipeline_id, request_id) DO NOTHING;
        """
        # MySQL uses INSERT IGNORE or ON DUPLICATE KEY UPDATE.
        # Wait, the migration was written in Postgres style? "ON CONFLICT DO NOTHING"
        # Since this is aiomysql, it is MySQL!
        # Let's fix the SQL syntax for MySQL.
        query_mysql = """
        INSERT IGNORE INTO token_usage_logs (
            request_id, pipeline_id, agent_name, provider, model,
            prompt_tokens, completion_tokens, total_tokens,
            cost_usd, latency_ms, metadata, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
        """
        
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        query_mysql,
                        (
                            record.request_id,
                            record.pipeline_id,
                            record.agent_name,
                            record.provider,
                            record.model,
                            record.prompt_tokens,
                            record.completion_tokens,
                            record.total_tokens,
                            record.cost_usd,
                            record.latency_ms,
                            json.dumps(record.metadata) if record.metadata else None,
                            record.created_at
                        )
                    )
                    await conn.commit()
        except Exception as e:
            logger.error(f"Failed to save token usage log safely: {str(e)}")

    @staticmethod
    async def fetch_by_pipeline(pipeline_id: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM token_usage_logs WHERE pipeline_id = %s ORDER BY created_at ASC;"
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                import aiomysql
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, (pipeline_id,))
                    rows = await cursor.fetchall()
                    return rows
        except Exception as e:
            logger.error(f"Error fetching tokens for pipeline {pipeline_id}: {str(e)}")
            return []

    @staticmethod
    async def aggregate_pipeline(pipeline_id: str) -> Dict[str, Any]:
        logs = await TokenUsageRepo.fetch_by_pipeline(pipeline_id)
        
        result = {
            "total_prompt_tokens": sum(log.get("prompt_tokens", 0) for log in logs),
            "total_completion_tokens": sum(log.get("completion_tokens", 0) for log in logs),
            "total_tokens": sum(log.get("total_tokens", 0) for log in logs),
            "total_cost_usd": sum(log.get("cost_usd", 0.0) or 0.0 for log in logs),
            "per_agent": {}
        }
        
        for log in logs:
            agent_name = log.get("agent_name", "unknown")
            if agent_name not in result["per_agent"]:
                result["per_agent"][agent_name] = {
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0,
                    "latency_count": 0,
                    "avg_latency_ms": 0.0
                }
            
            agent_stats = result["per_agent"][agent_name]
            agent_stats["total_tokens"] += log.get("total_tokens", 0)
            agent_stats["total_cost_usd"] += float(log.get("cost_usd", 0.0) or 0.0)
            
            latency = log.get("latency_ms")
            if latency is not None:
                agent_stats["total_latency_ms"] += latency
                agent_stats["latency_count"] += 1
                
        for agent_name, stats in result["per_agent"].items():
            if stats["latency_count"] > 0:
                stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["latency_count"]
            else:
                stats["avg_latency_ms"] = 0.0
            
            del stats["total_latency_ms"]
            del stats["latency_count"]
            
        return result
