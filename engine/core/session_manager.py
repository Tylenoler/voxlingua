# Session management for VoxLingua

import uuid
import time
from datetime import datetime
from typing import Optional

from models.schemas import SessionInfo, CorrectionMode


class Session:
    """Represents a single conversation session."""

    def __init__(
        self,
        session_id: str = "",
        language: str = "en",
        scene: str = "daily_chat",
        voice_profile: str = "new_york",
    ):
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.created_at = datetime.now()
        self.language = language
        self.scene = scene
        self.voice_profile = voice_profile
        self.correction_mode = CorrectionMode()
        self.messages: list[dict] = []  # [{role, content, timestamp}]
        self.message_count = 0
        self.last_active = datetime.now()

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.message_count += 1
        self.last_active = datetime.now()

    def get_history(self, max_messages: int = 20) -> list[dict]:
        """Get recent message history for LLM context."""
        return [{"role": m["role"], "content": m["content"]}
                for m in self.messages[-max_messages:]]

    def to_info(self) -> SessionInfo:
        return SessionInfo(
            session_id=self.session_id,
            created_at=self.created_at,
            language=self.language,
            scene=self.scene,
            voice_profile=self.voice_profile,
            correction_mode=self.correction_mode,
            message_count=self.message_count,
            last_active=self.last_active,
        )

    @property
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        elapsed = (datetime.now() - self.last_active).total_seconds()
        return elapsed > timeout_minutes * 60

    def __repr__(self):
        return f"Session({self.session_id}, {self.language}, {self.scene})"


class SessionManager:
    """Manages all active sessions."""

    def __init__(self, timeout_minutes: int = 60):
        self._sessions: dict[str, Session] = {}
        self._timeout = timeout_minutes

    def create_session(
        self,
        language: str = "en",
        scene: str = "daily_chat",
        voice_profile: str = "new_york",
    ) -> Session:
        session = Session(
            language=language,
            scene=scene,
            voice_profile=voice_profile,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_expired(self._timeout):
            self.remove_session(session_id)
            return None
        return session

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        expired = [sid for sid, s in self._sessions.items()
                   if s.is_expired(self._timeout)]
        for sid in expired:
            self.remove_session(sid)
        return len(expired)

    @property
    def active_count(self) -> int:
        self.cleanup_expired()
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()
