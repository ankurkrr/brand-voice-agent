"""
Strict Input Validator for Agent 3
Enforces agent boundaries and rejects partial/sample data
"""
from typing import List, Dict, Tuple
from domain.models.agent3_request import BrandVoiceProfile, ContentBrief


class Agent3ValidationError(Exception):
    """Strict validation error for Agent 3"""
    def __init__(self, error_code: str, reason: str, field: str = ""):
        self.error_code = error_code
        self.reason = reason
        self.field = field
        super().__init__(f"{error_code}: {reason}")


def validate_brand_voice_strict(profile: BrandVoiceProfile) -> Tuple[bool, str]:
    """
    STRICT validation of Brand Voice Profile
    
    Enforces:
    - Must have profile_id (from Agent 1)
    - Cannot be sample/placeholder data
    - All required fields must be present
    
    Args:
        profile: Brand voice profile to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Raises:
        Agent3ValidationError: On any violation
    """
    # Check 1: Profile ID required (proves it's from Agent 1)
    if not profile.profile_id:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Brand voice profile must have profile_id from Agent 1. Cannot accept user-created voice data.",
            field="brand_voice_profile.profile_id"
        )
    
    # Check 2: Reject sample/placeholder data
    if profile.profile_id.upper() in ["SAMPLE", "SAMPLE_BRAND", "TEST", "PLACEHOLDER"]:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Cannot execute with sample/placeholder brand voice. Must use validated Agent 1 profile.",
            field="brand_voice_profile.profile_id"
        )
    
    # Check 3: Tone structure
    tone = profile.tone
    if not tone.get("primary"):
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Brand voice tone must have 'primary' field",
            field="brand_voice_profile.tone.primary"
        )
    
    if not tone.get("description"):
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Brand voice tone must have 'description' field",
            field="brand_voice_profile.tone.description"
        )
    
    # Check 4: At least one do/dont rule required
    if not profile.dos and not profile.donts:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Brand voice must have at least one 'do' or 'dont' rule",
            field="brand_voice_profile.dos"
        )
    
    return True, ""


def validate_content_brief_strict(brief: ContentBrief, platforms: List[str]) -> Tuple[bool, str]:
    """
    STRICT validation of Content Brief
    
    Enforces:
    - All required fields present
    - Blog outline required if blog platform selected
    - Key messages must be meaningful (not empty strings)
    
    Args:
        brief: Content brief to validate
        platforms: Selected platforms
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Raises:
        Agent3ValidationError: On any violation
    """
    # Check 1: Topic
    if not brief.topic or not brief.topic.strip():
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Content brief topic is required and cannot be empty",
            field="content_brief.topic"
        )
    
    # Check 2: Target audience
    if not brief.target_audience or not brief.target_audience.strip():
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Content brief target_audience is required and cannot be empty",
            field="content_brief.target_audience"
        )
    
    # Check 3: Key messages (at least one, no empty strings)
    if not brief.key_messages or len(brief.key_messages) == 0:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Content brief must have at least one key message",
            field="content_brief.key_messages"
        )
    
    empty_messages = [i for i, msg in enumerate(brief.key_messages) if not msg.strip()]
    if empty_messages:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            f"Content brief key_messages contain empty strings at indices: {empty_messages}",
            field="content_brief.key_messages"
        )
    
    # Check 4: CTA
    if not brief.cta or not brief.cta.strip():
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Content brief call_to_action is required and cannot be empty",
            field="content_brief.cta"
        )
    
    # Check 5: Blog outline required if blog platform selected
    if "blog" in platforms:
        if not brief.blog_outline or len(brief.blog_outline) < 2:
            raise Agent3ValidationError(
                "EXECUTION_REJECTED",
                "Blog platform requires blog_outline with at least 2 H2 headings",
                field="content_brief.blog_outline"
            )
    
    return True, ""


def validate_platforms_strict(platforms: List[str]) -> Tuple[bool, str]:
    """
    STRICT validation of platforms list
    
    Enforces:
    - Must not be empty
    - Only known platforms
    - No duplicates
    
    Args:
        platforms: List of platforms
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Raises:
        Agent3ValidationError: On any violation
    """
    # Check 1: Not empty
    if not platforms or len(platforms) == 0:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Platforms list cannot be empty. Must specify at least one platform.",
            field="platforms"
        )
    
    # Check 2: Valid platforms only
    valid_platforms = {"blog", "linkedin", "twitter", "email"}
    invalid = set(platforms) - valid_platforms
    if invalid:
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            f"Unknown platforms: {list(invalid)}. Valid platforms: {list(valid_platforms)}",
            field="platforms"
        )
    
    # Check 3: No duplicates
    if len(platforms) != len(set(platforms)):
        raise Agent3ValidationError(
            "EXECUTION_REJECTED",
            "Platforms list contains duplicates",
            field="platforms"
        )
    
    return True, ""


def validate_all_strict(
    profile: BrandVoiceProfile,
    brief: ContentBrief,
    platforms: List[str]
) -> Dict:
    """
    Run all strict validations
    
    Returns error dict if validation fails, None if success
    
    Args:
        profile: Brand voice profile
        brief: Content brief
        platforms: Platforms list
        
    Returns:
        Error dict or None
    """
    try:
        validate_brand_voice_strict(profile)
        validate_content_brief_strict(brief, platforms)
        validate_platforms_strict(platforms)
        return None  # Success
        
    except Agent3ValidationError as e:
        return {
            "error": e.error_code,
            "reason": e.reason,
            "field": e.field
        }
    except Exception as e:
        return {
            "error": "EXECUTION_REJECTED",
            "reason": f"Unexpected validation error: {str(e)}",
            "field": ""
        }
