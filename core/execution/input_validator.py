"""
Input Validation for Agent 3
Validates brand voice profile and content brief before execution
"""
from typing import Dict, List, Tuple
from domain.models.agent3_request import BrandVoiceProfile, ContentBrief


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_brand_voice_profile(profile: BrandVoiceProfile) -> Tuple[bool, str]:
    """
    Validate Brand Voice Profile structure and content
    
    Args:
        profile: BrandVoiceProfile from Agent 1
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if profile is None:
            raise ValidationError("profile", "Brand Voice Profile object is missing/None")

        # Check tone structure
        if not profile.tone:
            raise ValidationError("tone", "Tone object is required")
        
        if "primary" not in profile.tone:
            raise ValidationError("tone.primary", "Primary tone is required")
        
        if not profile.tone["primary"]:
            raise ValidationError("tone.primary", "Primary tone cannot be empty")
        
        # Validate secondary tones is a list
        if "secondary" in profile.tone and not isinstance(profile.tone["secondary"], list):
            raise ValidationError("tone.secondary", "Secondary tones must be a list")
        
        # Check that at least one guidance exists (dos or donts)
        if not profile.dos and not profile.donts:
            raise ValidationError("rules", "At least one 'do' or 'dont' rule is required")
        
        return True, ""
        
    except ValidationError as e:
        return False, f"{e.field}: {e.message}"
    except Exception as e:
        return False, f"Unexpected validation error: {str(e)}"


def validate_content_brief(brief: ContentBrief) -> Tuple[bool, str]:
    """
    Validate Content Brief structure and content
    
    Args:
        brief: ContentBrief from Agent 2
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Required fields
        if not brief.topic or not brief.topic.strip():
            raise ValidationError("topic", "Topic is required and cannot be empty")
        
        if not brief.target_audience or not brief.target_audience.strip():
            raise ValidationError("target_audience", "Target audience is required")
        
        if not brief.key_messages or len(brief.key_messages) == 0:
            raise ValidationError("key_messages", "At least one key message is required")
        
        # Validate key messages are not empty
        empty_messages = [i for i, msg in enumerate(brief.key_messages) if not msg.strip()]
        if empty_messages:
            raise ValidationError("key_messages", f"Key message at index {empty_messages[0]} is empty")
        
        if not brief.cta or not brief.cta.strip():
            raise ValidationError("cta", "Call-to-action is required")
        
        # Blog outline should have at least 2 headings if provided
        if brief.blog_outline and len(brief.blog_outline) < 2:
            raise ValidationError("blog_outline", "Blog outline should have at least 2 H2 headings")
        
        return True, ""
        
    except ValidationError as e:
        return False, f"{e.field}: {e.message}"
    except Exception as e:
        return False, f"Unexpected validation error: {str(e)}"


def validate_platform_compatibility(
    profile: BrandVoiceProfile,
    brief: ContentBrief,
    platforms: List[str]
) -> Tuple[bool, str]:
    """
    Check for contradictions between brand voice, content brief, and platforms
    
    Args:
        profile: Brand voice profile
        brief: Content brief
        platforms: List of target platforms
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check if blog is in platforms but outline is missing
        if "blog" in platforms and not brief.blog_outline:
            raise ValidationError(
                "blog_outline",
                "Blog platform requires blog_outline in content brief"
            )
        
        # Check if keywords exist for SEO platforms
        if "blog" in platforms and not brief.keywords:
            # Warning but not error
            print("[WARNING] Blog platform recommended to have keywords for SEO")
        
        return True, ""
        
    except ValidationError as e:
        return False, f"{e.field}: {e.message}"
    except Exception as e:
        return False, f"Unexpected validation error: {str(e)}"


def validate_all_inputs(
    profile: BrandVoiceProfile,
    brief: ContentBrief,
    platforms: List[str]
) -> Tuple[bool, str]:
    """
    Run all validations
    
    Args:
        profile: Brand voice profile
        brief: Content brief
        platforms: Target platforms
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate profile
    valid, error = validate_brand_voice_profile(profile)
    if not valid:
        return False, f"Brand Voice Profile validation failed: {error}"
    
    # Validate brief
    valid, error = validate_content_brief(brief)
    if not valid:
        return False, f"Content Brief validation failed: {error}"
    
    # Validate compatibility
    valid, error = validate_platform_compatibility(profile, brief, platforms)
    if not valid:
        return False, f"Platform compatibility validation failed: {error}"
    
    return True, "All validations passed"
