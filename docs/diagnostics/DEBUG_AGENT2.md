# Agent 2 Save Issue - What to Check

## CRITICAL: Check Your FastAPI Server Console NOW

When you trigger Agent 2 from the frontend, look for these log messages in your FastAPI server console:

### Expected Log Flow (if working):
```
[AGENT2] Skipping brand check for brand_id xxx (In-Memory Workflow)
[AGENT2] Gathering web signals for fingerprinting...
[AGENT2] Profile not loaded yet. Attempting to fetch from database...
[AGENT2] ✅ Fetched voice profile for saving: yyy
[AGENT2] Saving content brief to database...
[ContentBriefsRepo] Inserting split content brief...
[AGENT2] ✅ Content brief saved to DB: zzz
```

### If Profile NOT Found:
```
[AGENT2] Profile not loaded yet. Attempting to fetch from database...
[AGENT2] ⚠️ WARNING: Cannot save to DB - no voice profile exists for brand xxx
[AGENT2] Switching to deferred save mode (save via /ideation/save later)
[AGENT2] ⏭️ Skipping DB persistence (will save later via /ideation/save)
```

### If Error Occurs:
```
[IDEATION_ROUTER] Error: <error message>
Traceback...
```

## What to Share:
1. **Copy the ENTIRE console output** when Agent 2 triggers
2. **Check if you see the warning**: "Cannot save to DB - no voice profile exists"
3. **Look for any Python exceptions or traceback**

## Quick Database Check:
Run this SQL query to verify what's actually in the database:

```sql
-- Check if Agent 1 profile exists
SELECT 
    profile_id, 
    brand_id, 
    status, 
    created_at 
FROM voice_profiles_human 
ORDER BY created_at DESC 
LIMIT 5;

-- Check if Agent 2 briefs exist
SELECT 
    brief_id,
    brand_id,
    voice_profile_id,
    topic,
    created_at
FROM content_briefs_human
ORDER BY created_at DESC
LIMIT 5;
```

## Most Likely Causes:
1. ❌ Profile fetch returns None (Agent 1 didn't save or used different brand_id)
2. ❌ Silent exception in ContentBriefsRepo.insert_content_brief
3. ❌ Autocommit not working (transaction rolled back)
4. ❌ FK constraint violation (profile_id mismatch)
