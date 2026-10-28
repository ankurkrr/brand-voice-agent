# data/repos/generated_content.py

from data.db.session import get_pool
import uuid
import json
from datetime import datetime

class GeneratedContentRepo:
    """
    Repository for Agent-3 Generated Content.
    Persists platform-native outputs.
    """

    @staticmethod
    async def save_generation(
        brand_id: str,
        voice_profile_id: str,
        output_data: dict,
        brief_id: str = None,
        metadata: dict = None
    ):
        """
        Save generated content to the database.
        
        Args:
            brand_id: UUID of the brand
            voice_profile_id: UUID of the used voice profile
            output_data: The full Agent 3 response dictionary
            brief_id: Optional UUID of the content brief used
            metadata: Optional dictionary of execution metadata
            
        Returns:
            dict: Persisted record
        """
        print(f"[GeneratedContentRepo] Saving generation for brand: {brand_id}")
        pool = await get_pool()
        gen_id = str(uuid.uuid4())
        
        output_json = json.dumps(output_data)
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO generated_content 
                    (id, brand_id, voice_profile_id, content_brief_id, output_json, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (gen_id, brand_id, voice_profile_id, brief_id, output_json, metadata_json)
                )
                await conn.commit()
                
                print(f"[GeneratedContentRepo] Content saved: {gen_id}")
                return {
                    "id": gen_id,
                    "brand_id": brand_id,
                    "created_at": datetime.now().isoformat()
                }

    @staticmethod
    async def fetch_generations_by_brand(brand_id: str, limit: int = 20, brief_id: str = None):
        """
        Fetch recent generations for a brand.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if brief_id:
                    query = """
                    SELECT * FROM generated_content 
                    WHERE brand_id = %s AND content_brief_id = %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """
                    params = (brand_id, brief_id, limit)
                else:
                    query = """
                    SELECT * FROM generated_content 
                    WHERE brand_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """
                    params = (brand_id, limit)

                await cursor.execute(query, params)
                rows = await cursor.fetchall()
                if not rows:
                    return []
                
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                results = [dict(zip(columns, row)) for row in rows]
                return results
    # (intentionally no fetch by generation id - regeneration resolves only by profile_id then brand_id)

    @staticmethod
    async def delete_brand_content(brand_id: str):
        """
        Delete all generated content for a brand (V1).
        """
        print(f"[GeneratedContentRepo] Deleting content for brand: {brand_id}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM generated_content WHERE brand_id = %s",
                    (brand_id,)
                )
                return True