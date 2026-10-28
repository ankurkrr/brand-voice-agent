"""
Voice Compliance Detector for Agent 3
Detects violations of brand voice rules in generated content
"""
from typing import List, Dict, Tuple
from domain.models.agent3_request import BrandVoiceProfile


class VoiceViolation:
    """Represents a detected voice violation"""
    def __init__(self, violation_type: str, detail: str, location: str):
        self.violation_type = violation_type  # "forbidden_phrase", "dont_rule", etc.
        self.detail = detail
        self.location = location  # Which platform/field
    
    def __repr__(self):
        return f"VoiceViolation({self.violation_type}: {self.detail} in {self.location})"


def detect_forbidden_phrases(
    content: str,
    forbidden_phrases: List[str],
    location: str
) -> List[VoiceViolation]:
    """
    Detect forbidden phrases in content
    
    Args:
        content: Generated content to check
        forbidden_phrases: List of banned phrases
        location: Where this content is (e.g., "blog.title")
        
    Returns:
        List of violations found
    """
    violations = []
    content_lower = content.lower()
    
    for phrase in forbidden_phrases:
        if phrase.lower() in content_lower:
            violations.append(VoiceViolation(
                violation_type="forbidden_phrase",
                detail=f"Found forbidden phrase: '{phrase}'",
                location=location
            ))
    
    return violations


def detect_all_violations(
    response: Dict,
    profile: BrandVoiceProfile
) -> List[VoiceViolation]:
    """
    Detect all voice violations across all platforms
    
    Args:
        response: Generated content response (dict)
        profile: Brand voice profile with rules
        
    Returns:
        List of all violations found
    """
    all_violations = []
    
    # Check blog
    if "blog" in response:
        blog = response["blog"]
        all_violations.extend(detect_forbidden_phrases(
            blog.get("title", ""), 
            profile.forbidden_phrases,
            "blog.title"
        ))
        all_violations.extend(detect_forbidden_phrases(
            blog.get("content", ""), 
            profile.forbidden_phrases,
            "blog.content"
        ))
    
    # Check LinkedIn
    if "linkedin" in response:
        all_violations.extend(detect_forbidden_phrases(
            response["linkedin"].get("post", ""),
            profile.forbidden_phrases,
            "linkedin.post"
        ))
    
    # Check Twitter
    if "twitter" in response:
        thread = response["twitter"].get("thread", [])
        for i, tweet in enumerate(thread):
            all_violations.extend(detect_forbidden_phrases(
                tweet,
                profile.forbidden_phrases,
                f"twitter.thread[{i}]"
            ))
    
    # Check Email
    if "email" in response:
        email = response["email"]
        all_violations.extend(detect_forbidden_phrases(
            email.get("subject", ""),
            profile.forbidden_phrases,
            "email.subject"
        ))
        all_violations.extend(detect_forbidden_phrases(
            email.get("body", ""),
            profile.forbidden_phrases,
            "email.body"
        ))
    
    return all_violations


def format_violation_report(violations: List[VoiceViolation]) -> str:
    """
    Format violations into a readable report for rewrite instruction
    
    Args:
        violations: List of detected violations
        
    Returns:
        Formatted string for LLM instruction
    """
    if not violations:
        return ""
    
    report = "VOICE COMPLIANCE VIOLATIONS DETECTED:\n\n"
    
    for i, violation in enumerate(violations, 1):
        report += f"{i}. {violation.violation_type.upper()}\n"
        report += f"   Location: {violation.location}\n"
        report += f"   Issue: {violation.detail}\n\n"
    
    report += "\nREWRITE INSTRUCTIONS:\n"
    report += "- Remove or replace ALL forbidden phrases listed above\n"
    report += "- Maintain the same core message and information\n"
    report += "- Keep the same platform formatting and structure\n"
    report += "- Return the complete corrected JSON output\n"
    
    return report
