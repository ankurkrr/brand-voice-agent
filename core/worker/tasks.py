from core.worker.celery_app import celery_app
from core.pipelines.ingestion import ingest_content
from core.agents.v1.agent2_ideation import run_agent2_ideation
import asyncio

# Wrapper to run async functions in Celery sync worker
def run_async(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

@celery_app.task(bind=True, name="ingest_content_task")
def ingest_content_task(self, brand_name: str, input_type: str, input_value: str, file_content: str = None, file_extension: str = None):
    """
    Async wrapper for content ingestion pipeline.
    """
    # Note: file_content passed as base64 or bytes might need handling if strictly JSON.
    # Celery JSON serializer handles unicode strings. For binary files, might need encoding.
    # For now, assuming input_value (text/url) is the primary use case for background tasks.
    
    try:
        # We need to run the async pipeline function
        # Since Celery workers are typically synchronous, we use asyncio.run or existing loop
        # But ingest_content relies on DB pool which might need to be initialized in the worker process.
        
        # NOTE: DB connection pooling in Celery needs care. 
        # For simplicity in this refactor, we assume the async chain manages its connections.
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            ingest_content(
                brand_name=brand_name,
                input_type=input_type,
                input_value=input_value,
                file_content=file_content, # Warning: Passing large files via Broker is anti-pattern
                file_extension=file_extension
            )
        )
        loop.close()
        return result
    except Exception as e:
        self.retry(exc=e, countdown=5, max_retries=3)

@celery_app.task(bind=True, name="ideation_task")
def ideation_task(self, brand_id: str, topic: str, market: str, region: str, content_goal: str):
    """
    Async wrapper for Agent-2 ideation.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            run_agent2_ideation(
                brand_id=brand_id,
                topic=topic,
                market=market,
                region=region,
                content_goal=content_goal
            )
        )
        loop.close()
        return result
    except Exception as e:
        self.retry(exc=e, countdown=5, max_retries=3)
