# data/repos/voice_profiles.py

from data.db.session import get_pool
import uuid
import json

class VoiceProfilesRepo:

    @staticmethod
    async def get_latest_version(brand_id: str) -> int:
        """Fetch the latest version number for a brand's voice profile (from human table)."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT MAX(version) FROM voice_profiles_human WHERE brand_id = %s",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else 0

    @staticmethod
    async def get_active_profile(brand_id: str, persona_id: str = None):
        """
        Fetch the latest usable voice profile.
        
        Args:
            brand_id: Brand UUID
            persona_id: (Optional) Persona UUID for V2 execution
            
        Returns:
            Dict with profile data (compatible with BrandVoiceProfile model)
        """
        pool = await get_pool()
        
        # CASE 1: V2 Persona-specific execution
        if persona_id:
            print(f"[REPO][GET_ACTIVE_PROFILE] Fetching V2 Persona: {persona_id}")
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        SELECT profile_data, dimensional_scores 
                        FROM voice_personas 
                        WHERE persona_id = %s AND brand_id = %s
                        """,
                        (persona_id, brand_id)
                    )
                    row = await cursor.fetchone()
                    
                    if not row:
                        print(f"[REPO][GET_ACTIVE_PROFILE] Persona {persona_id} not found")
                        # Fallback optional? No, strict enforcement per contracts.
                        raise ValueError(f"Persona {persona_id} not found for brand {brand_id}")
                        
                    profile_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    dim_scores = row[1] if isinstance(row[1], dict) else (json.loads(row[1]) if row[1] else {})
                    
                    # Ensure compatibility with BrandVoiceProfile model
                    # The persona's profile_data should already match the structure
                    return {
                        **profile_data,
                        "dimensional_scores": dim_scores,
                        "persona_id": persona_id
                    }

        # CASE 2: V1 Standard Execution (Legacy)
        print(f"[REGEN][REPO][ACTIVE_PROFILE] Querying brand_id={brand_id}")

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # DEBUG: Check ALL profiles first to see what's there
                await cursor.execute(
                    "SELECT profile_id, status, version FROM voice_profiles_human WHERE brand_id = %s", 
                    (brand_id,)
                )
                all_rows = await cursor.fetchall()
                print(f"[REGEN][REPO][ACTIVE_PROFILE] Total profiles found for brand: {len(all_rows)}")
                for r in all_rows:
                    print(f"[REGEN][REPO][ACTIVE_PROFILE] - profile_id={r[0]} status={r[1]} version={r[2]}")

                # Actual Query - Get latest active/approved or draft? 
                # "Active" usually means the latest one we allow usage of.
                # Logic: Sort by created_at DESC (LIFO)
                sql = """
                    SELECT profile_id, status, version, explicit_rules, system_prompt
                    FROM voice_profiles_human
                    WHERE brand_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                
                await cursor.execute(sql, (brand_id,))
                
                row = await cursor.fetchone()
                if row:
                    print(f"[REGEN][REPO][ACTIVE_PROFILE] Selected profile_id={row[0]} status={row[1]} version={row[2]}")
                    
                    explicit_rules = row[3] if isinstance(row[3], dict) else json.loads(row[3])
                    
                    return {
                        "profile_id": row[0],
                        "status": row[1],
                        "version": row[2],
                        "tone": explicit_rules.get("tone"),
                        "dos": explicit_rules.get("dos", []),
                        "donts": explicit_rules.get("donts", []),
                        "forbidden_phrases": explicit_rules.get("forbidden_phrases", []),
                        "preferred_vocabulary": explicit_rules.get("preferred_vocabulary", []),
                        "examples": explicit_rules.get("examples", []) # Ensure examples existence
                        # Missing: system_prompt? Not strictly needed for V1 Agent3 model but good to have
                    }
                else:
                    print(f"[REGEN][REPO][ACTIVE_PROFILE] Final selection: NONE")
                    return None
    
    @staticmethod
    async def save_profile(brand_id: str, profile_data: dict):
        if profile_data.get("version") == "v2":
            raise RuntimeError("save_profile() must not be used for V2 profiles")

        """
        Dual-write save to Human (Phase 1) and Machine (Phase 2) tables.
        Appends new version.
        """
        print(f"[VoiceProfilesRepo] Saving new version (Split Mode) for brand: {brand_id}")
        pool = await get_pool()
        profile_id = str(uuid.uuid4())
        machine_id = str(uuid.uuid4())
        
        # Determine next version
        current_version = await VoiceProfilesRepo.get_latest_version(brand_id)
        next_version = current_version + 1
        
        # Inject version
        profile_data['version'] = next_version
        
        # Extract Phase 1 Data (Human)
        system_prompt = profile_data.get('system_prompt', '')
        rules = profile_data.get('rules', {})
        tone = profile_data.get('tone', {})
        
        explicit_rules = {
            "dos": rules.get('dos', []),
            "donts": rules.get('donts', []),
            "forbidden_phrases": rules.get('forbidden_phrases', []),
            "preferred_vocabulary": rules.get('preferred_vocabulary', []),
            "tone": tone,
            "audio_profile": profile_data.get("audio_profile") # NEW: Persist audio metrics
        }
        explicit_json = json.dumps(explicit_rules)
        
        print(f"[VoiceProfilesRepo] Saving new version (Phase 1 Human Only) for brand: {brand_id}")


        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 1. Insert Human Record (Phase 1)
                await cursor.execute(
                    """
                    INSERT INTO voice_profiles_human 
                    (profile_id, brand_id, system_prompt, explicit_rules, version, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'DRAFT', NOW())
                    """,
                    (profile_id, brand_id, system_prompt, explicit_json, next_version)
                )
                
                # No explicit commit - pool has autocommit=True
                
                print(f"[VoiceProfilesRepo] Split Profile saved: ID={profile_id}, Version={next_version}")
                return {**profile_data, "id": profile_id, "version": next_version}

    @staticmethod
    async def get_profile(profile_id: str):
        """
        Fetch composite profile by joining human and machine tables.
        Retains backward compatibility structure.
        """
        print(f"[REGEN][REPO][GET_PROFILE] Attempting fetch for profile_id={profile_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT h.*, m.dimensional_scores, m.implicit_rules, m.embeddings_meta
                    FROM voice_profiles_human h
                    LEFT JOIN voice_profiles_machine m
                    ON h.profile_id = m.profile_id
                    AND m.version = 2
                    WHERE h.profile_id = %s
                    LIMIT 1
                    """,
                    (profile_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    print(f"[REGEN][REPO][GET_PROFILE] FOUND - brand_id={data['brand_id']} version={data['version']} status={data['status']}")
                    
                    # Reconstruct legacy JSON structure for compatibility
                    # Parse JSONs if string
                    explicit = data['explicit_rules'] if isinstance(data['explicit_rules'], dict) else json.loads(data['explicit_rules'])
                    dim = data['dimensional_scores']
                    if dim and isinstance(dim, str): dim = json.loads(dim)
                    
                    implicit = data['implicit_rules']
                    if implicit and isinstance(implicit, str): implicit = json.loads(implicit)

                    # Construct composite object
                    composite_data = {
                        "id": data['profile_id'],
                        "profile_id": data['profile_id'], # Explicitly return profile_id for frontend compatibility
                        "brand_id": data['brand_id'],
                        "system_prompt": data['system_prompt'],
                        "rules": explicit, # Flattened explicit rules
                        "tone": explicit.get('tone'),
                        "dimensional_scores": dim,
                        "style_metrics": implicit,
                        "version": data['version'],
                        "status": data['status'],
                        "created_at": str(data['created_at'])
                    }
                    
                    # Store inner data for 'profile_data' key if needed by consumers
                    # Most consumers read keys directly from dict, so this flattening is good.
                    return composite_data
                    
                print(f"[REGEN][REPO][GET_PROFILE] NOT FOUND")
                return None

    @staticmethod
    async def get_profile_by_brand_id(brand_id: str):
        """Fetch latest profile for brand (Joined)"""
        print(f"[REGEN][REPO][GET_BY_BRAND_ID] Attempting fetch for brand_id={brand_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT h.*, m.dimensional_scores, m.implicit_rules, m.embeddings_meta
                    FROM voice_profiles_human h
                    LEFT JOIN voice_profiles_machine m
                    ON h.profile_id = m.profile_id
                    AND m.version = 2
                    WHERE h.brand_id = %s 
                    ORDER BY h.version DESC LIMIT 1
                    """,
                    (brand_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    print(f"[REGEN][REPO][GET_BY_BRAND_ID] FOUND profile_id={data['profile_id']} version={data['version']} status={data['status']}")
                    
                    # Reconstruct
                    explicit = data['explicit_rules'] if isinstance(data['explicit_rules'], dict) else json.loads(data['explicit_rules'])
                    
                    composite_data = {
                        "id": data['profile_id'],
                        "profile_id": data['profile_id'], # Explicitly return profile_id
                        "brand_id": data['brand_id'],
                        "system_prompt": data['system_prompt'],
                        "rules": explicit, 
                        "tone": explicit.get('tone'),
                        "dimensional_scores": data['dimensional_scores'], # Raw/None is fine
                        "version": data['version'],
                        "status": data['status']
                    }
                    return composite_data
                print(f"[REGEN][REPO][GET_BY_BRAND_ID] NOT FOUND")
                return None

    @staticmethod
    async def update_human_profile(profile_id: str, updates: dict):
        """
        UPDATE Phase 1 (Human) data.
        Updates explicit rules system prompt.
        """
        print(f"[VoiceProfilesRepo] Updating Human Phase 1 Data for: {profile_id}")
        pool = await get_pool()
        
        # Prepare explicit rules JSON
        explicit_json = json.dumps(updates.get('explicit_rules', {}))
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE voice_profiles_human
                    SET system_prompt = %s, explicit_rules = %s
                    WHERE profile_id = %s
                    """,
                    (updates.get('system_prompt'), explicit_json, profile_id)
                )
                # No explicit commit - pool has autocommit=True
                print("[VoiceProfilesRepo] Human profile updated")
                return True

    @staticmethod
    async def update_stats(brand_id: str, accepted: bool):
        # Stats are now essentially just "Status" in the human table
        # We'll map 'accepted' -> 'APPROVED' status
        status = 'APPROVED' if accepted else 'DRAFT'
        print(f"[VoiceProfilesRepo] Updating status to {status} for brand: {brand_id}")
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Find latest profile first
                await cursor.execute("SELECT profile_id FROM voice_profiles_human WHERE brand_id=%s ORDER BY version DESC LIMIT 1", (brand_id,))
                row = await cursor.fetchone()
                if not row: return None
                
                pid = row[0]
                await cursor.execute(
                    "UPDATE voice_profiles_human SET status = %s WHERE profile_id = %s",
                    (status, pid)
                )
                # No explicit commit - pool has autocommit=True
                return {"status": status}

    @staticmethod
    async def is_locked(brand_id: str) -> bool:
        """Check if profile is locked (via voice_profiles_human status)"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT status, explicit_rules FROM voice_profiles_human WHERE brand_id = %s ORDER BY version DESC LIMIT 1",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return False
                # Check explicit status or rules-level lock
                if row[0] == 'LOCKED':
                    return True
                data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                return data.get('stats', {}).get('locked', False) if data else False

    @staticmethod
    async def update_rules(brand_id: str, new_rules: dict, new_tone: str):
        print(f"[VoiceProfilesRepo] Updating rules for brand: {brand_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch current data from voice_profiles_human
                await cursor.execute(
                    "SELECT profile_id, explicit_rules FROM voice_profiles_human WHERE brand_id = %s ORDER BY version DESC LIMIT 1",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    print("[VoiceProfilesRepo] Profile not found for rules update")
                    return None
                
                profile_id = row[0]
                data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                if not data:
                    data = {}
                
                # Check lock
                if data.get('stats', {}).get('locked', False):
                    print("[VoiceProfilesRepo] Profile is locked, cannot update")
                    return None
                
                # Update rules in explicit_rules JSON
                data['dos'] = new_rules.get('dos', [])
                data['donts'] = new_rules.get('donts', [])
                data['tone'] = new_tone 
                
                # Save back to voice_profiles_human
                updated_json = json.dumps(data)
                
                await cursor.execute(
                    """
                    UPDATE voice_profiles_human
                    SET explicit_rules = %s
                    WHERE profile_id = %s
                    """,
                    (updated_json, profile_id)
                )
                # No explicit commit - pool has autocommit=True
                
                # Fetch updated row
                await cursor.execute(
                    "SELECT * FROM voice_profiles_human WHERE profile_id = %s",
                    (profile_id,)
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    print(f"[VoiceProfilesRepo] Rules updated")
                    return result
                return None

    @staticmethod
    async def update_feedback_stats(profile_id: str, new_stats: dict):
        """
        Update the feedback stats in the dedicated table.
        Used by the feedback router.
        """
        print(f"[VoiceProfilesRepo] Updating feedback stats for profile: {profile_id}")
        pool = await get_pool()
        
        # Extract fields
        acceptance_rate = new_stats.get('acceptance_rate', 0.0)
        total_events = new_stats.get('total_feedback_events', 0)
        accept_count = new_stats.get('accept_count', 0)
        rewrite_count = new_stats.get('rewrite_count', 0)

        # We need brand_id for the stats table. Fetch it first if not passed (it should be in profile, but we only have ID here)
        # Actually, we can fetch it or just rely on the join if we had it. 
        # Let's fetch brand_id quickly.
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Get Brand ID
                await cursor.execute("SELECT brand_id FROM voice_profiles_human WHERE profile_id = %s", (profile_id,))
                row = await cursor.fetchone()
                if not row: return None
                brand_id = row[0]

                # UPSERT Statement
                await cursor.execute(
                    """
                    INSERT INTO voice_profile_feedback_stats 
                    (profile_id, brand_id, acceptance_rate, total_events, accept_count, rewrite_count, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        acceptance_rate = VALUES(acceptance_rate),
                        total_events = VALUES(total_events),
                        accept_count = VALUES(accept_count),
                        rewrite_count = VALUES(rewrite_count),
                        last_updated = NOW()
                    """,
                    (profile_id, brand_id, acceptance_rate, total_events, accept_count, rewrite_count)
                )
                return True

    @staticmethod
    async def get_feedback_stats(profile_id: str):
        """
        Fetch stats from dedicated table.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT acceptance_rate, total_events, accept_count, rewrite_count 
                    FROM voice_profile_feedback_stats 
                    WHERE profile_id = %s
                    """,
                    (profile_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return {
                        "acceptance_rate": float(row[0]),
                        "total_feedback_events": row[1],
                        "accept_count": row[2],
                        "rewrite_count": row[3]
                    }
                return None

    @staticmethod
    async def update_status(profile_id: str, new_status: str):
        """
        Update profile approval status (DRAFT → APPROVED / REJECTED)
        
        Args:
            profile_id: Voice profile UUID
            new_status: One of 'DRAFT', 'APPROVED', 'REJECTED'
            
        Returns:
            dict: Updated profile record or None if not found
        """
        allowed_statuses = ['DRAFT', 'APPROVED', 'REJECTED']
        if new_status not in allowed_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {allowed_statuses}")
        
        print(f"[VoiceProfilesRepo] Updating status to {new_status} for profile: {profile_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE voice_profiles_human SET status = %s WHERE profile_id = %s",
                    (new_status, profile_id)
                )
                # No explicit commit - pool has autocommit=True
                
                # Fetch updated record
                await cursor.execute(
                    "SELECT * FROM voice_profiles_human WHERE profile_id = %s",
                    (profile_id,)
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    print(f"[VoiceProfilesRepo] Status updated to {new_status}")
                    return result
                print("[VoiceProfilesRepo] Profile not found")
                return None

    @staticmethod
    async def is_approved(profile_id: str) -> bool:
        """
        Check if a profile is in APPROVED status
        
        Args:
            profile_id: Voice profile UUID
            
        Returns:
            bool: True if status='APPROVED', False otherwise
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT status FROM voice_profiles_human WHERE profile_id = %s",
                    (profile_id,)
                )
                row = await cursor.fetchone()
                return row and row[0] == 'APPROVED'

    @staticmethod
    async def save_profile_v2(
        brand_id: str,
        parent_profile_id: str,
        agent1_v2_output: dict
    ):
        """
        Persist Agent-1 V2 output explicitly into the machine table.
        Does NOT touch human table.
        """

        print("[V2 SAVE]", agent1_v2_output)

        pool = await get_pool()
        machine_id = str(uuid.uuid4())

        # Explicit V2 version (do not auto-increment)
        version = 2

        # Fail fast — never allow silent corruption
        if "dimensional_scores" not in agent1_v2_output:
            raise ValueError("V2 Save Error: dimensional_scores missing")
        if "implicit_rules" not in agent1_v2_output:
            raise ValueError("V2 Save Error: implicit_rules missing")

        dim_json = json.dumps(agent1_v2_output["dimensional_scores"])
        implicit_json = json.dumps(agent1_v2_output["implicit_rules"])
        embed_json = json.dumps(agent1_v2_output.get("embeddings_meta", {}))
        
        # New Multi-Modal Fields
        audio_json = json.dumps(agent1_v2_output.get("audio_profile", {}))
        transcript_json = json.dumps(agent1_v2_output.get("transcript_meta", {}))
        modalities_json = json.dumps(agent1_v2_output.get("modalities", []))

        # ============================
        # ============================
        # 🔍 DEBUG: V2 MACHINE SAVE
        # ============================
        print("🧠 [MACHINE SAVE] profile_id =", parent_profile_id)
        print("🧠 [MACHINE SAVE] version = 2")
        print("🧠 [MACHINE SAVE] dimensional_scores =", dim_json)
        print("🧠 [MACHINE SAVE] implicit_rules =", implicit_json)

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO voice_profiles_machine
                    (id, profile_id, brand_id, dimensional_scores, implicit_rules, embeddings_meta, audio_profile, transcript_meta, modalities, version, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        machine_id,
                        parent_profile_id,
                        brand_id,
                        dim_json,
                        implicit_json,
                        embed_json,
                        audio_json,
                        transcript_json,
                        modalities_json,
                        version
                    )
                )

        return {
            "profile_id": parent_profile_id,
            "brand_id": brand_id,
            "version": version,
            "dimensional_scores": agent1_v2_output["dimensional_scores"],
            "implicit_rules": agent1_v2_output["implicit_rules"],
            "audio_profile": agent1_v2_output.get("audio_profile"),
            "transcript_meta": agent1_v2_output.get("transcript_meta"),
            "modalities": agent1_v2_output.get("modalities")
        }

    @staticmethod
    async def get_human_profile_raw(profile_id: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT profile_id, brand_id, system_prompt, explicit_rules, version
                    FROM voice_profiles_human
                    WHERE profile_id = %s
                    """,
                    (profile_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))

                # Parse JSON explicitly
                import json
                data["explicit_rules"] = (
                    data["explicit_rules"]
                    if isinstance(data["explicit_rules"], dict)
                    else json.loads(data["explicit_rules"])
                )

                return data

    @staticmethod
    async def delete_brand_profiles(brand_id: str):
        """
        Delete all profiles for a brand (Machine V2 + Human V1).
        Machine must be deleted first due to FK constraint.
        """
        print(f"[VoiceProfilesRepo] Deleting profiles for brand: {brand_id}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Delete Machine Profiles (V2) first — FK references human
                await cursor.execute(
                    "DELETE FROM voice_profiles_machine WHERE brand_id = %s",
                    (brand_id,)
                )
                
                # Delete Human Profiles (V1)
                await cursor.execute(
                    "DELETE FROM voice_profiles_human WHERE brand_id = %s",
                    (brand_id,)
                )
                return True
        @staticmethod
        async def create_persona(
            persona_id: str,
            brand_id: str,
            persona_name: str,
            parent_persona_id: str,
            profile_data: dict,
            dimensional_scores: dict,
            status: str
        ):
            query = """
            INSERT INTO voice_personas (
                persona_id,
                brand_id,
                persona_name,
                parent_persona_id,
                profile_data,
                dimensional_scores,
                status,
                created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
            """
            await db.execute(
                query,
                (
                    persona_id,
                    brand_id,
                    persona_name,
                    parent_persona_id,
                    json.dumps(profile_data),
                    json.dumps(dimensional_scores),
                    status
                )
            )
