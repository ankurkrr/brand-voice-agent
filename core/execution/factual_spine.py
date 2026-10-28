"""
Factual Spine Guard for Agent 3
Ensures all platforms reference all key messages (prevents divergence)
"""
from typing import List, Dict
import hashlib


def hash_key_messages(key_messages: List[str]) -> str:
    """
    Create a hash of key messages for tracking
    
    Args:
        key_messages: List of key messages from content brief
        
    Returns:
        SHA256 hash of concatenated key messages
    """
    combined = "|".join(sorted(key_messages))
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def check_message_coverage(content: str, key_messages: List[str]) -> List[str]:
    """
    Check which key messages are referenced in content
    
    Args:
        content: Generated content text
        key_messages: List of key messages to check for
        
    Returns:
        List of missing key messages
    """
    content_lower = content.lower()
    missing = []
    
    for message in key_messages:
        # Simple keyword extraction (this could be more sophisticated)
        # Extract key terms from the message (words > 3 chars)
        keywords = [word.strip().lower() for word in message.split() if len(word) > 3]
        
        # Check if at least 50% of keywords are present
        found_count = sum(1 for kw in keywords if kw in content_lower)
        coverage = found_count / len(keywords) if keywords else 0
        
        if coverage < 0.5:  # Less than 50% coverage
            missing.append(message)
    
    return missing


def validate_factual_spine(response: Dict, key_messages: List[str]) -> Dict[str, List[str]]:
    """
    Validate that all platforms reference all key messages
    
    Args:
        response: Generated content response
        key_messages: List of key messages from content brief
        
    Returns:
        Dictionary mapping platform to list of missing messages
    """
    platform_issues = {}
    
    # Check blog
    if "blog" in response:
        blog_content = response["blog"].get("content", "")
        missing = check_message_coverage(blog_content, key_messages)
        if missing:
            platform_issues["blog"] = missing
    
    # Check LinkedIn
    if "linkedin" in response:
        linkedin_content = response["linkedin"].get("post", "")
        missing = check_message_coverage(linkedin_content, key_messages)
        if missing:
            platform_issues["linkedin"] = missing
    
    # Check Twitter (combine all tweets)
    if "twitter" in response:
        twitter_content = " ".join(response["twitter"].get("thread", []))
        missing = check_message_coverage(twitter_content, key_messages)
        if missing:
            platform_issues["twitter"] = missing
    
    # Check Email
    if "email" in response:
        email_content = response["email"].get("body", "")
        missing = check_message_coverage(email_content, key_messages)
        if missing:
            platform_issues["email"] = missing
    
    return platform_issues


def format_spine_violation_report(platform_issues: Dict[str, List[str]]) -> str:
    """
    Format factual spine violations into a report
    
    Args:
        platform_issues: Dict mapping platform to missing messages
        
    Returns:
        Formatted report string
    """
    if not platform_issues:
        return ""
    
    report = "FACTUAL SPINE VIOLATIONS - Missing Key Messages:\n\n"
    
    for platform, missing_messages in platform_issues.items():
        report += f"Platform: {platform.upper()}\n"
        report += "Missing messages:\n"
        for msg in missing_messages:
            report += f"  - {msg}\n"
        report += "\n"
    
    report += "CORRECTION REQUIRED:\n"
    report += "- Each platform MUST reference ALL key messages\n"
    report += "- Rewrite to incorporate missing messages naturally\n"
    report += "- Do not drop facts to meet length constraints - rewrite more concisely\n"
    
    return report
