"""
VoxLingua — Pydantic Schemas

Shared data models used across the AI engine:
  - Audio/chat request/response models
  - Correction pipeline models (phoneme errors, scoring dimensions)
  - Session models
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CorrectionModeLevel(str, Enum):
    OFF = "off"
    MILD_ONLY = "mild_only"
    MEDIUM = "medium"
    ALL = "all"


class CorrectionMode(BaseModel):
    mode: str = Field(default="medium")
    interrupt_on_severe: bool = Field(default=True)


class PhonemeError(BaseModel):
    phoneme: str = Field(...)
    expected: str = Field(...)
    actual: str = Field(...)
    word: str = Field(default="")
    severity: str = Field(...)
    feedback: str = Field(default="")

    model_config = {"from_attributes": True}


class ScoreDimensions(BaseModel):
    phoneme_accuracy: float = Field(default=0.0, ge=0.0, le=100.0)
    fluency: float = Field(default=0.0, ge=0.0, le=100.0)
    prosody: float = Field(default=0.0, ge=0.0, le=100.0)
    completeness: float = Field(default=0.0, ge=0.0, le=100.0)

    model_config = {"from_attributes": True}


class CorrectionResult(BaseModel):
    level: str = Field(...)
    user_text: str = Field(default="")
    corrected_text: str = Field(default="")
    errors: list[PhonemeError] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    dimensions: ScoreDimensions = Field(default_factory=ScoreDimensions)

    model_config = {"from_attributes": True}


class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    language: str = "en"
    scene: str = "daily_chat"
    voice_profile: str = "new_york"
    correction_mode: CorrectionMode = Field(default_factory=CorrectionMode)
    message_count: int = 0
    last_active: datetime

    model_config = {"from_attributes": True}


class AudioInput(BaseModel):
    session_id: str = Field(default="")
    data: str = Field(...)
    format: str = Field(default="opus")
    sample_rate: int = Field(default=16000)


class ChatRequest(BaseModel):
    session_id: str = Field(default="")
    message: str = Field(...)
    language: str = Field(default="en")
    scene: str = Field(default="daily_chat")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: str = "en"


class VoiceProfile(BaseModel):
    profile_id: str
    name: str
    language: str = "en"
    is_default: bool = False


class SceneInfo(BaseModel):
    id: str
    name: str
    description: str = ""


class EngineStatus(BaseModel):
    status: str = "running"
    version: str = "1.0.0"
    llm_connected: bool = False
    active_sessions: int = 0
    connected_devices: int = 0


class WSMessageType(str, Enum):
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    AUDIO_INPUT = "audio_input"
    AUDIO_STREAM_START = "audio_stream_start"
    AUDIO_STREAM_CHUNK = "audio_stream_chunk"
    AUDIO_STREAM_END = "audio_stream_end"
    CORRECTION = "correction"
    SET_SCENE = "set_scene"
    SCENE_UPDATED = "scene_updated"
    SET_VOICE = "set_voice"
    VOICE_UPDATED = "voice_updated"
    SET_CORRECTION_MODE = "set_correction_mode"
    CORRECTION_MODE_UPDATED = "correction_mode_updated"
    ERROR = "error"


class WSMessage(BaseModel):
    type: str
    payload: dict = Field(default_factory=dict)
