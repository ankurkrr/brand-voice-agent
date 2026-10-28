"""
Execution Metadata Logger for Agent 3
Internal logging for debugging and auditing (NOT returned to user)
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, List
from domain.models.agent3_request import BrandVoiceProfile, ContentBrief


class ExecutionMetadata:
    """Internal execution envelope for Agent 3"""
    
    def __init__(
        self,
        agent: str = "agent3",
        model: str = "gemini-2.5-flash",
        voice_profile_hash: str = "",
        content_brief_hash: str = "",
        platform_rules_version: str = "v1.0",
        rewrite_count: int = 0,
        voice_violations: List[str] = None,
        platform_violations: List[str] = None,
        spine_violations: List[str] = None,
        timestamp: str = ""
    ):
        self.agent = agent
        self.model = model
        self.voice_profile_hash = voice_profile_hash
        self.content_brief_hash = content_brief_hash
        self.platform_rules_version = platform_rules_version
        self.rewrite_count = rewrite_count
        self.voice_violations = voice_violations or []
        self.platform_violations = platform_violations or []
        self.spine_violations = spine_violations or []
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            "agent": self.agent,
            "model": self.model,
            "voice_profile_hash": self.voice_profile_hash,
            "content_brief_hash": self.content_brief_hash,
            "platform_rules_version": self.platform_rules_version,
            "rewrite_count": self.rewrite_count,
            "voice_violations": self.voice_violations,
            "platform_violations": self.platform_violations,
            "spine_violations": self.spine_violations,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


def hash_voice_profile(profile: BrandVoiceProfile) -> str:
    """
    Create hash of brand voice profile for tracking
    
    Args:
        profile: Brand voice profile
        
    Returns:
        SHA256 hash (first 16 chars)
    """
    # Serialize profile deterministically
    profile_str = json.dumps({
        "tone": profile.tone,
        "dos": sorted(profile.dos),
        "donts": sorted(profile.donts),
        "forbidden_phrases": sorted(profile.forbidden_phrases),
        "preferred_vocabulary": sorted(profile.preferred_vocabulary)
    }, sort_keys=True)
    
    return hashlib.sha256(profile_str.encode()).hexdigest()[:16]


def hash_content_brief(brief: ContentBrief) -> str:
    """
    Create hash of content brief for tracking
    
    Args:
        brief: Content brief
        
    Returns:
        SHA256 hash (first 16 chars)
    """
    # Serialize brief deterministically
    brief_str = json.dumps({
        "topic": brief.topic,
        "target_audience": brief.target_audience,
        "key_messages": sorted(brief.key_messages),
        "keywords": sorted(brief.keywords),
        "cta": brief.cta,
        "blog_outline": brief.blog_outline
    }, sort_keys=True)
    
    return hashlib.sha256(brief_str.encode()).hexdigest()[:16]


def log_execution_metadata(metadata: ExecutionMetadata):
    """
    Log execution metadata (currently to console, could be DB later)
    
    Args:
        metadata: Execution metadata to log
    """
    print("\n" + "="*60)
    print("AGENT 3 EXECUTION METADATA (INTERNAL ONLY)")
    print("="*60)
    print(metadata.to_json())
    print("="*60 + "\n")
    
    # TODO: In production, store this in database:
    # - execution_logs table
    # - For debugging "why did this change?"
    # - For comparing outputs across versions
    # - For future audits
