"""
Platform Validators for Agent 3
Post-generation validation of platform-specific constraints
"""
from typing import Dict, List, Tuple
from core.execution.platform_rules import PLATFORM_RULES


class PlatformViolation:
    """Represents a platform constraint violation"""
    def __init__(self, platform: str, field: str, constraint: str, actual: any, limit: any):
        self.platform = platform
        self.field = field
        self.constraint = constraint
        self.actual = actual
        self.limit = limit
    
    def __repr__(self):
        return f"PlatformViolation({self.platform}.{self.field}: {self.constraint} - actual={self.actual}, limit={self.limit})"


def validate_blog(blog: Dict) -> List[PlatformViolation]:
    """Validate blog post constraints"""
    violations = []
    rules = PLATFORM_RULES["blog"]
    
    # Word count check
    content = blog.get("content", "")
    word_count = len(content.split())
    
    if word_count < rules["min_words"]:
        violations.append(PlatformViolation(
            "blog", "content", "min_words",
            actual=word_count, limit=rules["min_words"]
        ))
    
    if word_count > rules["max_words"]:
        violations.append(PlatformViolation(
            "blog", "content", "max_words",
            actual=word_count, limit=rules["max_words"]
        ))
    
    # Title check
    title = blog.get("title", "")
    if not title or len(title) < 10:
        violations.append(PlatformViolation(
            "blog", "title", "min_length",
            actual=len(title), limit=10
        ))
    
    return violations


def validate_linkedin(linkedin: Dict) -> List[PlatformViolation]:
    """Validate LinkedIn post constraints"""
    violations = []
    rules = PLATFORM_RULES["linkedin"]
    
    post = linkedin.get("post", "")
    char_count = len(post)
    
    if char_count > rules["max_chars"]:
        violations.append(PlatformViolation(
            "linkedin", "post", "max_chars",
            actual=char_count, limit=rules["max_chars"]
        ))
    
    if char_count < 100:  # Minimum viable post
        violations.append(PlatformViolation(
            "linkedin", "post", "min_chars",
            actual=char_count, limit=100
        ))
    
    return violations


def validate_twitter(twitter: Dict) -> List[PlatformViolation]:
    """Validate Twitter thread constraints"""
    violations = []
    rules = PLATFORM_RULES["twitter"]
    
    thread = twitter.get("thread", [])
    
    # Thread length check
    if len(thread) > rules["max_thread_length"]:
        violations.append(PlatformViolation(
            "twitter", "thread", "max_thread_length",
            actual=len(thread), limit=rules["max_thread_length"]
        ))
    
    # Individual tweet length check
    for i, tweet in enumerate(thread):
        if len(tweet) > rules["max_chars_per_tweet"]:
            violations.append(PlatformViolation(
                "twitter", f"thread[{i}]", "max_chars_per_tweet",
                actual=len(tweet), limit=rules["max_chars_per_tweet"]
            ))
    
    return violations


def validate_email(email: Dict) -> List[PlatformViolation]:
    """Validate email constraints"""
    violations = []
    rules = PLATFORM_RULES["email"]
    
    # Subject line check
    subject = email.get("subject", "")
    if len(subject) > rules["subject_max_chars"]:
        violations.append(PlatformViolation(
            "email", "subject", "subject_max_chars",
            actual=len(subject), limit=rules["subject_max_chars"]
        ))
    
    # Preview text check
    preview = email.get("preview", "")
    if len(preview) > rules["preview_max_chars"]:
        violations.append(PlatformViolation(
            "email", "preview", "preview_max_chars",
            actual=len(preview), limit=rules["preview_max_chars"]
        ))
    
    if len(preview) < rules["preview_min_chars"]:
        violations.append(PlatformViolation(
            "email", "preview", "preview_min_chars",
            actual=len(preview), limit=rules["preview_min_chars"]
        ))
    
    # Body word count check
    body = email.get("body", "")
    word_count = len(body.split())
    if word_count > rules["body_max_words"]:
        violations.append(PlatformViolation(
            "email", "body", "body_max_words",
            actual=word_count, limit=rules["body_max_words"]
        ))
    
    return violations


def validate_all_platforms(response: Dict) -> Tuple[bool, List[PlatformViolation]]:
    """
    Validate all platform outputs against constraints
    
    Args:
        response: Generated content response
        
    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    all_violations = []
    
    if "blog" in response:
        all_violations.extend(validate_blog(response["blog"]))
    
    if "linkedin" in response:
        all_violations.extend(validate_linkedin(response["linkedin"]))
    
    if "twitter" in response:
        all_violations.extend(validate_twitter(response["twitter"]))
    
    if "email" in response:
        all_violations.extend(validate_email(response["email"]))
    
    return len(all_violations) == 0, all_violations


def format_platform_violation_report(violations: List[PlatformViolation]) -> str:
    """Format platform violations into a readable report"""
    if not violations:
        return ""
    
    report = "PLATFORM CONSTRAINT VIOLATIONS:\n\n"
    
    for i, v in enumerate(violations, 1):
        report += f"{i}. {v.platform.upper()} - {v.field}\n"
        report += f"   Constraint: {v.constraint}\n"
        report += f"   Actual: {v.actual}, Limit: {v.limit}\n\n"
    
    return report
