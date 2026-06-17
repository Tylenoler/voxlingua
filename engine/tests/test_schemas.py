"""
Tests for models/schemas.py — Pydantic model creation, validation, serialization.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from models.schemas import (
    AudioInput,
    AudioOutput,
    ChatRequest,
    ChatResponse,
    PhonemeError,
    ScoreDimensions,
    ScoringResult,
    CorrectionResult,
    CorrectionMode,
    SessionInfo,
    VoiceProfile,
    WSHandshake,
    WSHandshakeAck,
)


class TestAudioInput:
    def test_valid(self):
        obj = AudioInput(session_id="s1", data="AAAA")
        assert obj.session_id == "s1"
        assert obj.format == "opus"  # default

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            AudioInput(session_id="s1", format="mp3", data="AAAA")

    def test_missing_session_id(self):
        with pytest.raises(ValidationError):
            AudioInput(data="AAAA")


class TestAudioOutput:
    def test_valid(self):
        obj = AudioOutput(session_id="s1", text="hello", data="BBBB")
        assert obj.sample_rate == 24000  # default
        assert obj.language == "en"       # default


class TestChatRequest:
    def test_valid(self):
        obj = ChatRequest(session_id="s1", message="Hello")
        assert obj.scene == "daily_chat"  # default

    def test_language_override(self):
        obj = ChatRequest(session_id="s1", message="Hola", language="es")
        assert obj.language == "es"


class TestChatResponse:
    def test_valid(self):
        obj = ChatResponse(session_id="s1", reply="Hi there!")
        assert obj.reply == "Hi there!"


class TestPhonemeError:
    def test_valid(self):
        obj = PhonemeError(phoneme="θ", expected="θ", actual="s", word="think")
        assert obj.severity == "medium"

    def test_severity_override(self):
        obj = PhonemeError(
            phoneme="θ", expected="θ", actual="s", word="think", severity="severe"
        )
        assert obj.severity == "severe"

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            PhonemeError(
                phoneme="θ", expected="θ", actual="s", word="think", severity="unknown"
            )


class TestScoreDimensions:
    def test_defaults(self):
        obj = ScoreDimensions()
        assert obj.phoneme_accuracy == 0.0
        assert obj.grammar == 0.0

    def test_partial(self):
        obj = ScoreDimensions(phoneme_accuracy=85.5, fluency=90.0)
        assert obj.phoneme_accuracy == 85.5
        assert obj.prosody == 0.0  # default


class TestScoringResult:
    def test_valid_pronunciation(self):
        obj = ScoringResult(
            type="pronunciation",
            user_text="hello",
            target_text="hello",
            overall_score=85.0,
            dimensions=ScoreDimensions(phoneme_accuracy=85.0),
        )
        assert obj.type == "pronunciation"

    def test_valid_conversation(self):
        obj = ScoringResult(
            type="conversation",
            user_text="hello",
            target_text="hello world",
            overall_score=70.0,
            dimensions=ScoreDimensions(grammar=75.0),
        )
        assert obj.overall_score == 70.0


class TestCorrectionResult:
    def test_valid(self):
        obj = CorrectionResult(
            level="mild",
            user_text="I think",
            corrected_text="I think",
            overall_score=85.0,
            dimensions=ScoreDimensions(),
        )
        assert obj.level == "mild"

    def test_with_errors(self):
        err = PhonemeError(phoneme="θ", expected="θ", actual="s", word="think")
        obj = CorrectionResult(
            level="medium",
            user_text="I sink",
            corrected_text="I think",
            errors=[err],
            overall_score=65.0,
            dimensions=ScoreDimensions(phoneme_accuracy=65.0),
        )
        assert len(obj.errors) == 1
        assert obj.errors[0].phoneme == "θ"

    def test_serialize(self):
        obj = CorrectionResult(
            level="mild",
            user_text="hello",
            corrected_text="hello",
            overall_score=90.0,
            dimensions=ScoreDimensions(),
        )
        data = obj.model_dump()
        assert data["level"] == "mild"
        assert data["overall_score"] == 90.0


class TestCorrectionMode:
    def test_default(self):
        obj = CorrectionMode()
        assert obj.mode == "medium"
        assert obj.interrupt_on_severe is True

    def test_off(self):
        obj = CorrectionMode(mode="off")
        assert obj.mode == "off"

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            CorrectionMode(mode="extreme")


class TestSessionInfo:
    def test_valid(self):
        now = datetime.now()
        obj = SessionInfo(
            session_id="sess-001",
            created_at=now,
            last_active=now,
        )
        assert obj.language == "en"
        assert obj.scene == "daily_chat"
        assert obj.message_count == 0

    def test_missing_dates(self):
        with pytest.raises(ValidationError):
            SessionInfo(session_id="sess-001")


class TestVoiceProfile:
    def test_valid(self):
        now = datetime.now()
        obj = VoiceProfile(
            profile_id="nyc01",
            name="New York",
            language="en",
            created_at=now,
        )
        assert obj.duration_sec == 0.0


class TestWSHandshake:
    def test_valid(self):
        obj = WSHandshake()
        assert obj.client == "voxlingua-mobile"
        assert obj.version == "1.0.0"

    def test_desktop(self):
        obj = WSHandshake(client="voxlingua-desktop", platform="android")
        assert obj.client == "voxlingua-desktop"


class TestWSHandshakeAck:
    def test_valid(self):
        obj = WSHandshakeAck(session_id="sess-001")
        assert obj.status == "ready"
        assert obj.server_version == "1.0.0"
