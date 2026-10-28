from typing import Optional, List
from data.db.session import get_pool
from core.orchestration.pipeline_state import PipelineState, PipelineStatus
import uuid
import json

class PipelineStateRepo:
    """
    Repository for managing persistent PipelineState.
    Replaces in-memory _pipeline_store.
    """

    @staticmethod
    async def create_pipeline(brand_id: str, mode: str = "v1") -> PipelineState:
        """Create a new pipeline state record."""
        pool = await get_pool()
        pipeline_id = str(uuid.uuid4())
        
        # Initial map for steps status (stored conceptually, but mapped to DB columns)
        # DB has individual status columns: agent1_status, agent2_status, agent3_status
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO pipeline_states 
                    (id, pipeline_id, brand_id, mode, 
                     agent1_status, agent2_status, agent3_status, created_at)
                    VALUES (%s, %s, %s, %s, 'PENDING', 'PENDING', 'NOT_STARTED', NOW())
                    """,
                    (str(uuid.uuid4()), pipeline_id, brand_id, mode)
                )
                await conn.commit()
                
        # Return initial state object
        return PipelineState(
            pipeline_id=pipeline_id,
            brand_id=brand_id,
            mode=mode,
            steps={
                "voice_profiling": "PENDING",
                "ideation": "PENDING",
                "execution": "NOT_STARTED"
            },
            status=PipelineStatus.IN_PROGRESS
        )

    @staticmethod
    async def get_pipeline(pipeline_id: str) -> Optional[PipelineState]:
        """Fetch pipeline state by ID."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM pipeline_states WHERE pipeline_id = %s LIMIT 1",
                    (pipeline_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                    
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
                
                # Map DB columns to PipelineState object
                # agent1_status etc. -> steps dict
                steps = {
                    "voice_profiling": data.get("agent1_status", "PENDING"),
                    "ideation": data.get("agent2_status", "PENDING"),
                    "execution": data.get("agent3_status", "NOT_STARTED")
                }
                
                return PipelineState(
                    pipeline_id=data["pipeline_id"],
                    brand_id=data["brand_id"],
                    mode=data["mode"],
                    status=PipelineStatus.IN_PROGRESS, # Derived or stored? DB doesn't have overall status col, assuming derived from steps
                    steps=steps,
                    voice_profile_id=data.get("agent1_profile_id"),
                    brief_id=data.get("agent2_brief_id"),
                    execution_id=data.get("agent3_execution_id"),
                    updated_at=data.get("updated_at")
                )

    @staticmethod
    async def update_agent_status(
        pipeline_id: str, 
        agent: str, 
        status: str, 
        artifact_id: Optional[str] = None
    ):
        """
        Update status for a specific agent step.
        agent: 'agent1', 'agent2', 'agent3'
        status: 'DRAFT', 'APPROVED', 'REJECTED', 'COMPLETED'
        """
        pool = await get_pool()
        
        column_map = {
            "agent1": ("agent1_status", "agent1_profile_id"),
            "agent2": ("agent2_status", "agent2_brief_id"),
            "agent3": ("agent3_status", "agent3_execution_id")
        }
        
        if agent not in column_map:
            raise ValueError(f"Invalid agent: {agent}")
            
        status_col, id_col = column_map[agent]
        
        query = f"UPDATE pipeline_states SET {status_col} = %s"
        params = [status]
        
        if artifact_id:
            query += f", {id_col} = %s"
            params.append(artifact_id)
            
        query += " WHERE pipeline_id = %s"
        params.append(pipeline_id)
        
        print(f"[PipelineStateRepo] Updating {agent} status: {status}, artifact: {artifact_id}")
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, tuple(params))
                await conn.commit()

    @staticmethod
    async def get_latest_pipeline_by_brand(brand_id: str) -> Optional[PipelineState]:
        """Helper to get the most recent pipeline for a brand."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT pipeline_id FROM pipeline_states WHERE brand_id = %s ORDER BY created_at DESC LIMIT 1",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return await PipelineStateRepo.get_pipeline(row[0])
                return None
