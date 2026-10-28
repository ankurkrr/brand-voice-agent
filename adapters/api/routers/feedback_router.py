"""
Profile feedback endpoint - Agent 1 completion
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from data.repos.voice_profiles import VoiceProfilesRepo
import json

router = APIRouter(prefix="/profiles", tags=["profiles"])


class FeedbackRequest(BaseModel):
    action: Literal["accept", "reject", "rewrite"]


class FeedbackResponse(BaseModel):
    profile_id: str
    action: str
    acceptance_rate: float
    rewrite_count: int
    total_feedback_events: int


@router.post("/{profile_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(profile_id: str, feedback: FeedbackRequest):
    """
    Agent 1 User Feedback Loop - Final ARD Requirement
    
    Records user feedback on generated voice profile:
    - "accept": User approves the voice profile
    - "reject": User rejects the voice profile  
    - "rewrite": User requests regeneration (counts as rejection)
    
    Updates:
    - acceptance_rate: Running percentage of accepts
    - rewrite_count: Total number of rewrite requests
    
    Args:
        profile_id: Voice profile UUID
        feedback: User feedback action
        
    Returns:
        Updated feedback metrics
    """
    print(f"[FEEDBACK] Received '{feedback.action}' for profile: {profile_id}")
    
    # Verify profile exists
    profile = await VoiceProfilesRepo.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    # Fetch current stats from dedicated table
    stats = await VoiceProfilesRepo.get_feedback_stats(profile_id) or {}
    
    # Current metrics
    total_events = stats.get('total_feedback_events', 0)
    accept_count = stats.get('accept_count', 0)
    rewrite_count = stats.get('rewrite_count', 0)
    
    # Update based on action
    total_events += 1
    
    if feedback.action == "accept":
        accept_count += 1
        print(f"[FEEDBACK] Accept count: {accept_count}/{total_events}")
        
    elif feedback.action == "reject":
        # Rejection only increments total
        print(f"[FEEDBACK] Rejection recorded total rejections")
        
    elif feedback.action == "rewrite":
        rewrite_count += 1
        print(f"[FEEDBACK] Rewrite request #{rewrite_count}")
    
    # Calculate new acceptance rate
    acceptance_rate = (accept_count / total_events) if total_events > 0 else 0.0
    
    # New stats dictionary
    new_stats = {
        'total_feedback_events': total_events,
        'accept_count': accept_count,
        'rewrite_count': rewrite_count,
        'acceptance_rate': round(acceptance_rate, 4) # Higher precision for DB
    }
    
    # Persist
    await VoiceProfilesRepo.update_feedback_stats(profile_id, new_stats)
    
    print(f"[FEEDBACK] Updated: acceptance_rate={acceptance_rate:.2%}")
    
    return FeedbackResponse(
        profile_id=profile_id,
        action=feedback.action,
        acceptance_rate=round(acceptance_rate, 2),
        rewrite_count=rewrite_count,
        total_feedback_events=total_events
    )


@router.get("/{profile_id}/stats")
async def get_profile_stats(profile_id: str):
    """
    Get current feedback statistics for a voice profile
    
    Returns:
        Current acceptance rate and rewrite count
    """
    # Verify profile exists logic is implicitly handled if stats returns None? 
    # Better to check existence first or just return empty stats if profile exists.
    # Logic: check profile exists first.
    
    profile = await VoiceProfilesRepo.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    stats = await VoiceProfilesRepo.get_feedback_stats(profile_id) or {}
    
    return {
        "profile_id": profile_id,
        "acceptance_rate": stats.get('acceptance_rate', 0.0),
        "rewrite_count": stats.get('rewrite_count', 0),
        "total_feedback_events": stats.get('total_feedback_events', 0)
    }
