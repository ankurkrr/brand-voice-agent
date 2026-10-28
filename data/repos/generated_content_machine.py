from data.db.session import get_pool
import uuid, json
from datetime import datetime

class GeneratedContentMachineRepo:

    @staticmethod
    async def save_generation(
        brand_id: str,
        persona_id: str,
        brief_id: str,
        output_data: dict,
        dimensional_scores: dict,
        hierarchy_depth: int,
        confidence_score: float,
        variants: dict = None,
        nuance_summary: dict = None
    ):
        pool = await get_pool()
        gen_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO generated_content_machine
                    (id, brand_id, persona_id, content_brief_id,
                     output_json, dimensional_scores, hierarchy_depth,
                     confidence_score, variants, nuance_summary, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    """,
                    (
                        gen_id,
                        brand_id,
                        persona_id,
                        brief_id,
                        json.dumps(output_data),
                        json.dumps(dimensional_scores),
                        hierarchy_depth,
                        confidence_score,
                        json.dumps(variants) if variants else None,
                        json.dumps(nuance_summary) if nuance_summary else None
                    )
                )
                await conn.commit()

        return {
            "id": gen_id,
            "execution_version": "v2",
            "created_at": datetime.now().isoformat()
        }
    @staticmethod
    async def fetch_generations_by_brand(brand_id: str, limit: int = 5, brief_id: str = None):
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if brief_id:
                    query = """
                    SELECT id, output_json, created_at
                    FROM generated_content_machine
                    WHERE brand_id = %s AND content_brief_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """
                    params = (brand_id, brief_id, limit)
                else:
                    query = """
                    SELECT id, output_json, created_at
                    FROM generated_content_machine
                    WHERE brand_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """
                    params = (brand_id, limit)

                await cursor.execute(query, params)
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    output_val = row[1]
                    if isinstance(output_val, str):
                        try:
                            output_val = json.loads(output_val)
                        except:
                            pass
                            
                    results.append({
                        "id": row[0],
                        "output_data": output_val,
                        "created_at": row[2]
                    })
                return results

    @staticmethod
    async def save_nuance_violations(violations: list, persona_id: str, platform: str = "all"):
        """
        Persist nuance detection logs.
        """
        if not violations:
            return

        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Prepare batch inserts
                values = []
                for v in violations:
                    v_id = str(uuid.uuid4())
                    # Map NuanceViolation dataclass to schema
                    values.append((
                        v_id,
                        persona_id,
                        "See generated_content_machine table", # generated_text placeholder (schema override) 
                        getattr(v, 'phrase', "")[:500],
                        v.reason,
                        v.severity.value,
                        v.suggestion,
                        platform,
                        "strict", # enforcement_mode
                        False     # was_blocked
                    ))

                await cursor.executemany(
                    """
                    INSERT INTO nuance_detections
                    (id, persona_id, generated_text, violation_phrase, violation_reason, 
                     severity, suggested_rewrite, platform, enforcement_mode, was_blocked, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    values
                )
                await conn.commit()

    @staticmethod
    async def delete_brand_content(brand_id: str):
        """
        Delete all generated content for a brand (V2 + Nuance).
        """
        print(f"[GeneratedContentMachineRepo] Deleting content for brand: {brand_id}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Nuance Detections linked to Persona? Or Generation?
                # Nuance detections table has `persona_id`. 
                # If we delete personas, we should delete nuance detections?
                # OR we delete by matching persona_id in voice_personas for this brand.
                
                await cursor.execute(
                     """
                     DELETE FROM nuance_detections 
                     WHERE persona_id IN (
                         SELECT persona_id FROM voice_personas WHERE brand_id = %s
                     )
                     """,
                     (brand_id,)
                )
                
                # Delete Machine Generations
                await cursor.execute(
                    "DELETE FROM generated_content_machine WHERE brand_id = %s",
                    (brand_id,)
                )
                return True
