from typing import Optional, Dict, Any
from data.db.session import get_pool
from datetime import datetime
import json
import uuid


class VoicePersonasRepo:

    @staticmethod
    async def create_persona(
        brand_id: str,
        persona_id: str,
        persona_name: str,
        profile_data: Dict[str, Any],
        dimensional_scores: Dict[str, Any],
        parent_persona_id: Optional[str] = None,
        status: str = "ACTIVE",
        persona_key: Optional[str] = None,
        persona_origin: str = "SYSTEM", 
        persona_overlay_prompt: Optional[str] = None,
        persona_scope: str = "OVERLAY",
        persona_version: int = 1
    ):
        pool = await get_pool()
        row_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO voice_personas (
                        id,
                        persona_id,
                        brand_id,
                        persona_name,
                        parent_persona_id,
                        profile_data,
                        dimensional_scores,
                        status,
                        persona_key,
                        persona_origin,
                        persona_overlay_prompt,
                        persona_scope,
                        persona_version,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        row_id,
                        persona_id,
                        brand_id,
                        persona_name,
                        parent_persona_id,
                        json.dumps(profile_data),
                        json.dumps(dimensional_scores),
                        status,
                        persona_key,
                        persona_origin,
                        persona_overlay_prompt,
                        persona_scope,
                        persona_version
                    )
                )

    @staticmethod
    async def get_persona(
        brand_id: str,
        persona_id: str
    ) -> Optional[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT profile_data, dimensional_scores, status, created_at,
                           persona_key, persona_origin, persona_overlay_prompt, persona_scope, persona_version
                    FROM voice_personas
                    WHERE brand_id = %s
                      AND persona_id = %s
                      AND status = 'ACTIVE'
                    LIMIT 1
                    """,
                    (brand_id, persona_id)
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                return {
                    **(json.loads(row[0]) if isinstance(row[0], str) else row[0]),
                    "persona_id": persona_id,
                    "dimensional_scores": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                    "status": row[2],
                    "created_at": row[3],
                    "persona_key": row[4],
                    "persona_origin": row[5],
                    "persona_overlay_prompt": row[6],
                    "persona_scope": row[7],
                    "persona_version": row[8]
                }

    @staticmethod
    async def get_latest_persona_by_brand(brand_id: str) -> Optional[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT persona_id
                    FROM voice_personas
                    WHERE brand_id = %s
                      AND status = 'ACTIVE'
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (brand_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return None
                return {"persona_id": row[0]}

    @staticmethod
    async def delete_brand_personas(brand_id: str):
        """
        Delete all personas for a brand.
        """
        print(f"[VoicePersonasRepo] Deleting personas for brand: {brand_id}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM voice_personas WHERE brand_id = %s",
                    (brand_id,)
                )
                return True
