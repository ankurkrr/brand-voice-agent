# Diagnostic Report: Agent 1 V2 Output NuIl/Empty Issue

**Issue Noted:**
Agent 1 V2 runs successfully, but the persisted output (explicit rules, dimensional scores) appears null or empty in the database/downstream.

**Root Cause Analysis:**
There is a **Schema Mismatch** between the `Agent1V2Response` output structure and the `VoiceProfilesRepo.save_profile` input expectations.

| Data Field | Agent 1 V2 Output Key | Repo `save_profile` Expectation | Result |
| :--- | :--- | :--- | :--- |
| **Explicit Rules** | `refined_explicit_rules` | `rules` | Repo finds `None`/Empty for `rules`, saving empty DOs/DONTs. |
| **Implicit Rules** | `implicit_rules` | `style_metrics` | Repo finds `None`, saving defaults. |
| **Dimensional Scores** | `dimensional_scores` | `dimensional_scores` | **Should Match**. If strict null, check if Agent 1 V2 validation is passing. |

**1. Explicit Rules Mismatch**
- **Agent 1 Output:**
  ```json
  "refined_explicit_rules": { "tone": ..., "dos": ... }
  ```
- **Repo Logic (`voice_profiles.py` line 42):**
  ```python
  rules = profile_data.get('rules', {})
  ```
- **Consequence:** `rules` is empty dict. `explicit_rules` column becomes a JSON with empty lists.

**2. Implicit Rules Mismatch**
- **Agent 1 Output:**
  ```json
  "implicit_rules": { ... }
  ```
- **Repo Logic (`voice_profiles.py` line 56):**
  ```python
  implicit_rules = profile_data.get('style_metrics', {})
  ```
- **Consequence:** Repo looks for `style_metrics`, finds nothing, defaults to `{}`.

**3. Dimensional Scores**
- **Mismatch:** The key `dimensional_scores` matches.
- **Why it might be null:** If `save_profile` extracts `dimensional_scores` but the `INSERT INTO voice_profiles_machine` (which we modified) receives a `None` value if the output wasn't passed correctly from the router.
- *Note:* Since the other fields are definitely mismatched, it's highly probable the orchestration layer is passing the raw Agent 1 output to the Repo without mapping keys.

**Recommendation (Do Not Fix requested)**
To resolve this, an **Adapter/Mapper** layer is needed between `run_agent1` and `VoiceProfilesRepo.save_profile` to rename keys:
- `refined_explicit_rules` -> `rules`
- `implicit_rules` -> `style_metrics`
