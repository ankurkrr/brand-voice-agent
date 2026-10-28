from typing import Dict, Any, Optional
import uuid
from datetime import datetime

class SessionStore:
    """
    Ephemeral in-memory store for agent outputs before final persistence.
    Enforces strict separation of draft state vs. persisted state.
    """
    _sessions: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_session(cls, brand_id: str) -> str:
        session_id = str(uuid.uuid4())
        cls._sessions[session_id] = {
            "session_id": session_id,
            "brand_id": brand_id,
            "created_at": datetime.now(),
            "agent1_output": None,  # V1 + V2 Contract
            "agent2_output": None,  # V1 + V2 Contract
            "agent3_output": None,  # Final Artifact
            "is_locked": False
        }
        return session_id

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        return cls._sessions.get(session_id)

    @classmethod
    def update_agent1(cls, session_id: str, output: Dict[str, Any]):
        if session_id in cls._sessions:
            cls._sessions[session_id]["agent1_output"] = output

    @classmethod
    def update_agent2(cls, session_id: str, output: Dict[str, Any]):
        if session_id in cls._sessions:
            cls._sessions[session_id]["agent2_output"] = output

    @classmethod
    def update_agent3(cls, session_id: str, output: Dict[str, Any]):
        if session_id in cls._sessions:
            cls._sessions[session_id]["agent3_output"] = output

    @classmethod
    def lock_session(cls, session_id: str):
        if session_id in cls._sessions:
            cls._sessions[session_id]["is_locked"] = True
            
    @classmethod
    def clear_session(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
