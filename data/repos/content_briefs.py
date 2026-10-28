# data/repos/content_briefs.py

from data.db.session import get_pool
import uuid
import json


class ContentBriefsRepo:
    """
    Repository for Agent-2 Content Briefs.
    
    BOUNDARY ENFORCEMENT:
    - Only Agent-2 writes to this table
    - Immutable records (no update methods)
    - Foreign key ensures voice profile exists before brief creation
    """

    @staticmethod
    async def insert_content_brief(
        brand_id: str,
        voice_profile_id: str,
        topic: str,
        content_brief_data: dict,
        fingerprint: str = None
    ):
        """
        Persist brief to Human (Phase 1) and Machine (Phase 2) tables.
        """
        print(f"[ContentBriefsRepo] Inserting split brief for brand: {brand_id}")
        pool = await get_pool()
        brief_id = str(uuid.uuid4())
        machine_id = str(uuid.uuid4())
        
        # Phase 1 Data (Human Strategy)
        brief_json = json.dumps(content_brief_data)
        
        # Phase 2 Data (Machine Signals)
        # Assuming content_brief_data might contain signal data we want to strip/move?
        # For now, we store fingerprint and placeholder constraints
        constraints = {"must_follow_voice": True}
        web_signals = {}  # In future, pull from search result
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 1. Insert Human Record
                await cursor.execute(
                    """
                    INSERT INTO content_briefs_human 
                    (brief_id, brand_id, voice_profile_id, topic, content_brief_data, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'DRAFT', NOW())
                    """,
                    (brief_id, brand_id, voice_profile_id, topic, brief_json)
                )
                
                # 2. Insert Machine Record
                await cursor.execute(
                    """
                    INSERT INTO content_briefs_machine
                    (id, brief_id, fingerprint, constraints, web_signals, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (machine_id, brief_id, fingerprint, json.dumps(constraints), json.dumps(web_signals))
                )
                
                # No explicit commit needed - pool has autocommit=True
                
                print(f"[ContentBriefsRepo] Split Brief created: {brief_id}")
                return {"id": brief_id, "brand_id": brand_id, "topic": topic, "status": "DRAFT"}

    @staticmethod
    def _normalize_composite_brief_record(record: dict) -> dict:
        """
        Normalize DB composite record into the canonical API shape.
        - Keep the brief payload only under `content_brief_data`
        - Keep `web_signals` only inside `content_brief_data`
        - Drop legacy duplicate aliases/hoisted fields
        """
        # Parse nested content brief payload.
        brief_data = record.get("content_brief_data", {})
        if isinstance(brief_data, str):
            brief_data = json.loads(brief_data)
        if not isinstance(brief_data, dict):
            brief_data = {}

        # Canonicalize UI fields to ui_presentation for both legacy and new records.
        ui_data = brief_data.get("ui_presentation", {})
        if not isinstance(ui_data, dict):
            ui_data = {}
        raw_strategy = brief_data.get("raw_strategy", {})
        if not isinstance(raw_strategy, dict):
            raw_strategy = {}

        for key in ("target_audience", "seo_keywords", "h2_outline", "key_takeaways"):
            if not ui_data.get(key):
                if brief_data.get(key):
                    ui_data[key] = brief_data.get(key)
                elif raw_strategy.get(key):
                    ui_data[key] = raw_strategy.get(key)

            # Remove duplicated keys from non-canonical locations.
            brief_data.pop(key, None)
            raw_strategy.pop(key, None)

        brief_data["ui_presentation"] = ui_data
        brief_data["raw_strategy"] = raw_strategy

        # Machine table signals are legacy; only use as fallback if nested signals are absent.
        machine_signals = record.get("web_signals")
        if isinstance(machine_signals, str) and machine_signals:
            machine_signals = json.loads(machine_signals)
        if machine_signals and not brief_data.get("web_signals"):
            brief_data["web_signals"] = machine_signals

        record["content_brief_data"] = brief_data

        # Parse JSON constraints if needed.
        if record.get("constraints") and isinstance(record["constraints"], str):
            record["constraints"] = json.loads(record["constraints"])

        # Remove legacy duplicated/aliased fields.
        for key in (
            "web_signals",
            "target_audience",
            "seo_keywords",
            "h2_outline",
            "key_takeaways",
        ):
            record.pop(key, None)

        return record

    @staticmethod
    async def get_brief(brief_id: str):
        """
        Adapter: Fetch brief and format for Agent 3 execution (Pydantic compatible).
        """
        data = await ContentBriefsRepo.fetch_content_brief_by_id(brief_id)
        if not data:
            raise ValueError(f"Content Brief {brief_id} not found")

        # Extract canonical nested data
        inner = data.get("content_brief_data", {})
        ui = inner.get("ui_presentation", {}) if isinstance(inner, dict) else {}
        raw = inner.get("raw_strategy", {}) if isinstance(inner, dict) else {}

        # Map to ContentBrief model fields (UI canonical + backward fallbacks).
        return {
            "topic": data.get("topic") or inner.get("topic"),
            "target_audience": (
                ui.get("target_audience")
                or inner.get("target_audience")
                or raw.get("target_audience")
                or "General Audience"
            ),
            "key_messages": (
                ui.get("key_takeaways")
                or inner.get("key_messages")
                or inner.get("key_takeaways")
                or raw.get("key_takeaways", [])
            ),
            "keywords": (
                ui.get("seo_keywords")
                or inner.get("keywords")
                or inner.get("seo_keywords")
                or raw.get("seo_keywords", [])
            ),
            "cta": inner.get("cta", "Call to Action"), # Default if missing
            "blog_outline": (
                ui.get("h2_outline")
                or inner.get("blog_outline")
                or inner.get("h2_outline")
                or raw.get("h2_outline", [])
            ),
        }

    @staticmethod
    async def fetch_content_brief_by_id(brief_id: str):
        """Fetch composite brief (Human + Machine)"""
        print(f"[ContentBriefsRepo] Fetching split brief: {brief_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT h.*, m.id as machine_id, m.fingerprint, m.web_signals, m.constraints 
                    FROM content_briefs_human h
                    LEFT JOIN content_briefs_machine m ON h.brief_id = m.brief_id
                    WHERE h.brief_id = %s LIMIT 1
                    """,
                    (brief_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))

                    data = ContentBriefsRepo._normalize_composite_brief_record(data)

                    print(f"[ContentBriefsRepo] Brief found")
                    return data
                
                print("[ContentBriefsRepo] Brief not found")
                return None

    @staticmethod
    async def fetch_content_briefs_by_brand_id(brand_id: str, topic: str = None):
        """Fetch all briefs for brand, optionally filtered by topic"""
        print(f"[ContentBriefsRepo] Fetching briefs for brand: {brand_id} topic_filter={topic}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                    SELECT h.*, m.id as machine_id, m.fingerprint, m.web_signals, m.constraints
                    FROM content_briefs_human h
                    LEFT JOIN content_briefs_machine m ON h.brief_id = m.brief_id
                    WHERE h.brand_id = %s
                """
                params = [brand_id]

                if topic:
                    query += " AND LOWER(h.topic) = LOWER(%s)"
                    params.append(topic)

                query += " ORDER BY h.created_at DESC"

                await cursor.execute(query, tuple(params))

                rows = await cursor.fetchall()
                
                if not rows: return []
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in rows:
                    res = dict(zip(columns, row))

                    results.append(ContentBriefsRepo._normalize_composite_brief_record(res))
                
                return results

    @staticmethod
    async def update_status(brief_id: str, new_status: str):
        """Update status in Human table"""
        allowed_statuses = ['DRAFT', 'APPROVED', 'REJECTED']
        if new_status not in allowed_statuses:
            raise ValueError(f"Invalid {new_status}")
        
        print(f"[ContentBriefsRepo] Updating status to {new_status} for brief: {brief_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE content_briefs_human SET status = %s WHERE brief_id = %s",
                    (new_status, brief_id)
                )
                # No explicit commit needed - pool has autocommit=True
                
                # Fetch
                await cursor.execute(
                    "SELECT * FROM content_briefs_human WHERE brief_id = %s",
                    (brief_id,)
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None

    @staticmethod
    async def is_approved(brief_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT status FROM content_briefs_human WHERE brief_id = %s",
                    (brief_id,)
                )
                row = await cursor.fetchone()
                return row and row[0] == 'APPROVED'

    @staticmethod
    async def delete_brand_briefs(brand_id: str):
        """
        Delete all briefs for a brand.
        """
        print(f"[ContentBriefsRepo] Deleting briefs for brand: {brand_id}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Delete Machine Briefs (via join delete or separate? Schema likely has brand_id on machine? No, only brief_id)
                # Need to find briefs first or DELETE using JOIN.
                # Simplest: DELETE FROM content_briefs_machine WHERE brief_id IN (SELECT brief_id FROM content_briefs_human WHERE brand_id = %s)
                
                await cursor.execute(
                    """
                    DELETE FROM content_briefs_machine 
                    WHERE brief_id IN (
                        SELECT brief_id FROM content_briefs_human WHERE brand_id = %s
                    )
                    """,
                    (brand_id,)
                )
                
                # Delete Human Briefs
                await cursor.execute(
                    "DELETE FROM content_briefs_human WHERE brand_id = %s",
                    (brand_id,)
                )
                return True
