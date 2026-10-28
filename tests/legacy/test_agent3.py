"""
Enhanced test suite for Agent 3 with safety validation features
Tests voice compliance rewrite loop, platform validation, and factual spine guard
"""
import pytest
from domain.models.agent3_request import Agent3Request, BrandVoiceProfile, ContentBrief
from domain.models.agent3_response import Agent3Response
from core.agents.v1.agent3_execution import run_agent3
from core.execution.compliance_detector import detect_forbidden_phrases, detect_all_violations
from core.execution.platform_validator import validate_blog, validate_twitter, validate_email
from core.execution.factual_spine import validate_factual_spine


# Sample test data
VALID_BRAND_VOICE = BrandVoiceProfile(
    tone={
        "primary": "Professional",
        "secondary": ["Empowering", "Clear"],
        "description": "Professional yet approachable"
    },
    dos=["Use active voice", "Keep sentences under 20 words"],
    donts=["Use jargon", "Write in passive voice"],
    forbidden_phrases=["leverage", "synergy", "utilize"],
    preferred_vocabulary=["use", "empower", "transform"]
)

VALID_CONTENT_BRIEF = ContentBrief(
    topic="AI in Marketing Automation",
    target_audience="Marketing professionals and CMOs",
    key_messages=[
        "AI saves 10+ hours of manual work per week",
        "Improves campaign accuracy by 40%",
        "Easy to implement in existing workflows"
    ],
    keywords=["AI marketing", "automation", "efficiency"],
    cta="Start your free trial today",
    blog_outline=["What is AI Marketing", "Benefits of AI", "How to Get Started"]
)


# === Compliance Detector Tests ===

def test_detect_forbidden_phrases():
    """Test detection of forbidden phrases"""
    content = "We should leverage our synergy to utilize AI effectively."
    violations = detect_forbidden_phrases(
        content,
        ["leverage", "synergy", "utilize"],
        "test.content"
    )
    
    assert len(violations) == 3
    assert all(v.violation_type == "forbidden_phrase" for v in violations)


def test_detect_all_violations_in_response():
    """Test violation detection across all platforms"""
    response = {
        "blog": {
            "title": "Leverage AI for Growth",
            "content": "Use synergy to improve results"
        },
        "linkedin": {"post": "Clean content here"},
        "twitter": {"thread": ["No violations"]},
        "email": {"subject": "Test", "body": "Utilize our platform"}
    }
    
    violations = detect_all_violations(response, VALID_BRAND_VOICE)
    
    # Should find "leverage" in blog.title, "synergy" in blog.content, "utilize" in email.body
    assert len(violations) == 3


# === Platform Validator Tests ===

def test_validate_blog_too_short():
    """Test blog validation - too few words"""
    blog = {
        "title": "Short Blog",
        "content": "This is way too short."  # Only 5 words
    }
    
    violations = validate_blog(blog)
    assert len(violations) > 0
    assert any(v.constraint == "min_words" for v in violations)


def test_validate_twitter_thread_too_long():
    """Test Twitter validation - tweet exceeds 280 chars"""
    twitter = {
        "thread": [
            "Valid tweet",
            "A" * 300  # 300 characters, exceeds 280 limit
        ]
    }
    
    violations = validate_twitter(twitter)
    assert len(violations) > 0
    assert any(v.constraint == "max_chars_per_tweet" for v in violations)


def test_validate_email_subject_too_long():
    """Test email validation - subject line too long"""
    email = {
        "subject": "A" * 100,  # 100 chars, exceeds 60 limit
        "preview": "Normal preview text here",
        "body": "Normal body"
    }
    
    violations = validate_email(email)
    assert len(violations) > 0
    assert any(v.constraint == "subject_max_chars" for v in violations)


# === Factual Spine Tests ===

def test_factual_spine_all_messages_present():
    """Test factual spine validation - all messages present"""
    response = {
        "blog": {
            "content": "AI saves 10+ hours every week and improves campaign accuracy by 40%. It's easy to implement in existing workflows."
        }
    }
    
    issues = validate_factual_spine(response, VALID_CONTENT_BRIEF.key_messages)
    assert "blog" not in issues  # No issues


def test_factual_spine_missing_message():
    """Test factual spine validation - missing key message"""
    response = {
        "blog": {
            "content": "AI saves time."  # Missing accuracy and implementation messages
        }
    }
    
    issues = validate_factual_spine(response, VALID_CONTENT_BRIEF.key_messages)
    assert "blog" in issues
    assert len(issues["blog"]) >= 2  # At least 2 messages missing


# === Integration Tests with Rewrite Loop ===

@pytest.mark.asyncio
async def test_agent3_with_valid_input():
    """Test Agent 3 with valid inputs (should pass without rewrites)"""
    request = Agent3Request(
        brand_voice_profile=VALID_BRAND_VOICE,
        content_brief=VALID_CONTENT_BRIEF,
        platforms=["blog", "linkedin", "twitter", "email"]
    )
    
    result = await run_agent3(request)
    
    # Should not have error
    assert "error" not in result
    
    # Should have all platforms
    assert "blog" in result
    assert "linkedin" in result
    assert "twitter" in result
    assert "email" in result


@pytest.mark.asyncio
async def test_agent3_rewrite_loop_triggers():
    """Test that rewrite loop triggers on violations"""
    # This test validates the rewrite mechanism exists
    # In practice, the LLM should avoid violations, but we're testing the safety net
    request = Agent3Request(
        brand_voice_profile=VALID_BRAND_VOICE,
        content_brief=VALID_CONTENT_BRIEF
    )
    
    result = await run_agent3(request)
    
    # Even if LLM generates violations, rewrite loop should fix them
    # or return error after MAX_REWRITE_ATTEMPTS
    if "error" not in result:
        # Success - validate no violations
        violations = detect_all_violations(result, VALID_BRAND_VOICE)
        assert len(violations) == 0
    else:
        # If error, should be one of the expected violation errors
        assert result["error"] in [
            "VOICE_COMPLIANCE_FAILED",
            "PLATFORM_VALIDATION_FAILED",
            "FACTUAL_SPINE_FAILED"
        ]


@pytest.mark.asyncio
async def test_agent3_metadata_logging():
    """Test that execution metadata is generated (though not returned)"""
    request = Agent3Request(
        brand_voice_profile=VALID_BRAND_VOICE,
        content_brief=VALID_CONTENT_BRIEF
    )
    
    result = await run_agent3(request)
    
    # Metadata should be logged internally but NOT in response
    assert "metadata" not in result
    assert "voice_profile_hash" not in result
    assert "execution_metadata" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
