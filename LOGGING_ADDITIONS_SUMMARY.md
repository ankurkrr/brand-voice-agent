# Regeneration Flow Logging Additions

## Overview
Added structured, minimal, high-signal logging to the regeneration flow to deterministically understand why regeneration fails. All logging uses `print()` with `[REGEN]` prefix for consistent filtering.

## Files Modified

### 1. `adapters/api/routers/orchestration_router.py`
**Function**: `regenerate_profile(profile_id, request)`

#### Added Log Points:

**[1] API Entry Point**
```python
print(f"[REGEN][API][ENTRY] incoming_id={profile_id} request_url={request.url} request_method={request.method} session_id={request.query_params.get('session_id')}")
```
- Logs the exact ID received, HTTP method, URL, and session
- Allows tracing of the initial request

**[2] Profile ID Resolution - Initial Attempt**
```python
print(f"[REGEN][RESOLVE][PROFILE_ID] Attempting resolution as profile_id")
profile = await VoiceProfilesRepo.get_profile(profile_id)
```
- Logs the first resolution attempt (treating input as profile_id)

**[3] Profile ID Resolution - Found**
```python
print(f"[REGEN][RESOLVE][PROFILE_ID] Result=FOUND resolved_brand_id={brand_id}")
```
- Logs successful resolution with the extracted brand_id

**[4] Profile ID Resolution - Not Found**
```python
print(f"[REGEN][RESOLVE][PROFILE_ID] Result=NOT FOUND, attempting as brand_id")
```
- Indicates profile resolution failed, fallback to brand_id attempt

**[5] Brand ID Resolution - Fallback Attempt**
```python
print(f"[REGEN][RESOLVE][BRAND_ID] Treating incoming_id as brand_id, attempting fetch")
```
- Logs fallback to brand_id resolution

**[6] Brand ID Resolution - Found**
```python
print(f"[REGEN][RESOLVE][BRAND_ID] Result=FOUND brand_id={brand_id}")
```
- Logs successful brand_id resolution

**[7] Brand ID Resolution - Not Found**
```python
print(f"[REGEN][RESOLVE][BRAND_ID] Result=NOT FOUND")
```
- Logs failed brand_id resolution

**[8] Error - Could Not Resolve ID**
```python
print(f"[REGEN][ERROR][CAUSE] incoming_id={profile_id} could_not_resolve_to=profile_or_brand resolved_brand_id=None")
```
- Logs the exact reason for 404 error (ID not found as profile or brand)

**[9] Active Profile Check Input**
```python
print(f"[REGEN][ACTIVE_CHECK][INPUT] brand_id={brand_id}")
```
- Logs the brand_id being checked for active profiles

**[10] Active Profile Check - Not Found Error**
```python
print(f"[REGEN][ERROR][CAUSE] incoming_id={profile_id} resolved_brand_id={brand_id} active_profile_result=NONE")
```
- Logs the exact state when no active profile exists (400 error)

**[11] Active Profile Check - Success**
```python
print(f"[REGEN][ACTIVE_CHECK] Previous Active Profile: profile_id={old_active_id} status={active_profile['status']} version={active_profile['version']}")
```
- Logs the selected active profile details

**[12] Brand Data Retrieval Start**
```python
print(f"[REGEN][GEN][START] brand_name={brand_name} brand_id={brand_id} previous_profile_id={old_active_id}")
```
- Logs start of generation with all context

**[13] Brand Data Missing Error**
```python
print(f"[REGEN][ERROR][CAUSE] incoming_id={profile_id} resolved_brand_id={brand_id} active_profile_result={old_active_id} brand_data_missing=True")
```
- Logs the exact state when brand data is missing (500 error)

**[14] Success Path**
```python
print(f"[REGEN][SUCCESS] incoming_id={profile_id} resolved_brand_id={brand_id} old_profile_id={old_active_id} new_profile_version={new_version}")
```
- Logs complete success with old and new version info

**[15] Generation Exception**
```python
print(f"[REGEN][ERROR][CAUSE] incoming_id={profile_id} resolved_brand_id={brand_id} active_profile_result={old_active_id} generation_exception={str(e)}")
```
- Logs complete state when generation fails with exception

---

### 2. `data/repos/voice_profiles.py`
**Functions**: `get_profile()`, `get_latest_active_profile()`, `get_profile_by_brand_id()`

#### Added Log Points:

**[1] `get_profile()` - Entry**
```python
print(f"[REGEN][REPO][GET_PROFILE] Attempting fetch for profile_id={profile_id}")
```
- Logs the profile_id lookup attempt

**[2] `get_profile()` - Found**
```python
print(f"[REGEN][REPO][GET_PROFILE] FOUND - brand_id={data['brand_id']} version={data['version']} status={data['status']}")
```
- Logs successful profile retrieval with brand_id, version, and status

**[3] `get_profile()` - Not Found**
```python
print(f"[REGEN][REPO][GET_PROFILE] NOT FOUND")
```
- Logs failed profile lookup

**[4] `get_latest_active_profile()` - Entry**
```python
print(f"[REGEN][REPO][ACTIVE_PROFILE] Querying brand_id={brand_id}")
```
- Logs the brand_id being queried

**[5] `get_latest_active_profile()` - All Profiles Found**
```python
print(f"[REGEN][REPO][ACTIVE_PROFILE] Total profiles found for brand: {len(all_rows)}")
for r in all_rows:
    print(f"[REGEN][REPO][ACTIVE_PROFILE] - profile_id={r[0]} status={r[1]} version={r[2]}")
```
- Logs all available profiles for the brand (crucial for debugging why selection failed)

**[6] `get_latest_active_profile()` - Selected Profile**
```python
print(f"[REGEN][REPO][ACTIVE_PROFILE] Selected profile_id={row[0]} status={row[1]} version={row[2]}")
```
- Logs the selected active profile

**[7] `get_latest_active_profile()` - No Selection**
```python
print(f"[REGEN][REPO][ACTIVE_PROFILE] Final selection: NONE")
```
- Logs when no profile matches the criteria

**[8] `get_profile_by_brand_id()` - Entry**
```python
print(f"[REGEN][REPO][GET_BY_BRAND_ID] Attempting fetch for brand_id={brand_id}")
```
- Logs the brand_id lookup attempt (read-only, for fallback resolution)

**[9] `get_profile_by_brand_id()` - Found**
```python
print(f"[REGEN][REPO][GET_BY_BRAND_ID] FOUND profile_id={data['profile_id']} version={data['version']} status={data['status']}")
```
- Logs successful lookup with profile details

**[10] `get_profile_by_brand_id()` - Not Found**
```python
print(f"[REGEN][REPO][GET_BY_BRAND_ID] NOT FOUND")
```
- Logs failed lookup

---

## Log Flow Example - Success Case

```
[REGEN][API][ENTRY] incoming_id=brand-123 request_url=http://... request_method=POST session_id=sess-456
[REGEN][RESOLVE][PROFILE_ID] Attempting resolution as profile_id
[REGEN][REPO][GET_PROFILE] Attempting fetch for profile_id=brand-123
[REGEN][REPO][GET_PROFILE] NOT FOUND
[REGEN][RESOLVE][PROFILE_ID] Result=NOT FOUND, attempting as brand_id
[REGEN][RESOLVE][BRAND_ID] Treating incoming_id as brand_id, attempting fetch
[REGEN][RESOLVE][BRAND_ID] Result=FOUND brand_id=brand-123
[REGEN][ACTIVE_CHECK][INPUT] brand_id=brand-123
[REGEN][REPO][ACTIVE_PROFILE] Querying brand_id=brand-123
[REGEN][REPO][ACTIVE_PROFILE] Total profiles found for brand: 3
[REGEN][REPO][ACTIVE_PROFILE] - profile_id=prof-1 status=REJECTED version=1
[REGEN][REPO][ACTIVE_PROFILE] - profile_id=prof-2 status=APPROVED version=2
[REGEN][REPO][ACTIVE_PROFILE] - profile_id=prof-3 status=DRAFT version=3
[REGEN][REPO][ACTIVE_PROFILE] Selected profile_id=prof-3 status=DRAFT version=3
[REGEN][ACTIVE_CHECK] Previous Active Profile: profile_id=prof-3 status=DRAFT version=3
[REGEN][GEN][START] brand_name=ACME Corp brand_id=brand-123 previous_profile_id=prof-3
[REGEN][SUCCESS] incoming_id=brand-123 resolved_brand_id=brand-123 old_profile_id=prof-3 new_profile_version=4
```

---

## Log Flow Example - Failure Case (ID Not Found)

```
[REGEN][API][ENTRY] incoming_id=invalid-id request_url=http://... request_method=POST session_id=sess-456
[REGEN][RESOLVE][PROFILE_ID] Attempting resolution as profile_id
[REGEN][REPO][GET_PROFILE] Attempting fetch for profile_id=invalid-id
[REGEN][REPO][GET_PROFILE] NOT FOUND
[REGEN][RESOLVE][PROFILE_ID] Result=NOT FOUND, attempting as brand_id
[REGEN][RESOLVE][BRAND_ID] Treating incoming_id as brand_id, attempting fetch
[REGEN][RESOLVE][BRAND_ID] Result=NOT FOUND
[REGEN][ERROR][CAUSE] incoming_id=invalid-id could_not_resolve_to=profile_or_brand resolved_brand_id=None
```

---

## Logging Benefits

1. **Deterministic ID Resolution**: See exactly how the input ID was interpreted (profile_id or brand_id)
2. **DB State Visibility**: All profiles for a brand are logged before selection, showing why a specific one was chosen
3. **Decision Point Clarity**: Every decision boundary has a log entry showing the branch taken
4. **Error Context**: All error cases log the complete state (incoming_id, resolved_brand_id, active_profile_result)
5. **Success Confirmation**: Success path logs both old and new versions for archival tracking
6. **No Control Flow Changes**: Logging is purely additive—no try/except blocks added, no logic changed

---

## Design Principles Applied

- ✅ All logs use `print()` only (no logging frameworks)
- ✅ Every log prefixed with `[REGEN]` for filtering
- ✅ Logs placed at decision boundaries (before if/else branches)
- ✅ No existing logs removed
- ✅ No try/except blocks added
- ✅ No exceptions swallowed
- ✅ Minimal, high-signal information (IDs, results, statuses)
- ✅ Consistent format across all log levels
