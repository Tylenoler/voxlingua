"""
pytest conftest — shared fixtures and mocks for all VoxLingua engine tests.

All external model dependencies (Whisper, CosyVoice, Wav2Vec2, OpenAI) are
mocked so tests run fast and offline.
"""

from __future__ import annotations

import os
import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

# Ensure engine is importable
_engine_dir = os.path.join(os.path.dirname(__file__), "..")
if _engine_dir not in sys.path:
    sys.path.insert(0, _engine_dir)


# ── global mocks applied once per session ───────────────────────


@pytest.fixture(autouse=True, scope="session")
def _mock_heavy_imports():
    """Prevent tests from trying to load real ML models."""
    patches = [
        patch.dict("sys.modules", {
            "whisper": MagicMock(),
            "cosyvoice": MagicMock(),
            "cosyvoice.cli": MagicMock(),
            "cosyvoice.cli.cosyvoice": MagicMock(),
            "torchaudio": MagicMock(),
            "torch": MagicMock(),
            "transformers": MagicMock(),
        }),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


# ── sample data fixtures ────────────────────────────────────────


@pytest.fixture
def sample_audio_16k() -> np.ndarray:
    """500 ms of 16 kHz sine wave (mock speech)."""
    t = np.linspace(0, 0.5, 8000, endpoint=False)
    return (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)


@pytest.fixture
def sample_audio_24k() -> np.ndarray:
    """500 ms of 24 kHz sine wave."""
    t = np.linspace(0, 0.5, 12000, endpoint=False)
    return (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)


@pytest.fixture
def sample_text() -> str:
    return "I think this is a good idea."


@pytest.fixture
def sample_audio_b64(sample_audio_16k) -> str:
    """Base64-encoded PCM f32 audio at 16 kHz."""
    import base64
    pcm = sample_audio_16k.astype(np.float32).tobytes()
    return base64.b64encode(pcm).decode("utf-8")


@pytest.fixture
def sample_session_id() -> str:
    return "test-sess-001"


# ── mocked engine fixtures ──────────────────────────────────────


@pytest.fixture
def mock_stt_engine():
    """Mock STT engine returning canned transcription."""
    from core.stt_engine import WhisperSTTEngine, set_stt_engine

    engine = MagicMock(spec=WhisperSTTEngine)
    engine.is_loaded.return_value = True
    engine.transcribe.return_value = {
        "text": "I think this is a good idea.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 0.3, "text": "I think this is a good idea."}
        ],
        "duration": 0.5,
    }
    set_stt_engine(engine)
    return engine


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine returning sine-wave audio."""
    from core.tts_engine import CosyVoiceEngine, set_tts_engine

    engine = MagicMock(spec=CosyVoiceEngine)
    engine.is_loaded.return_value = True
    engine.SAMPLE_RATE = 24000
    engine.list_voices.return_value = [
        {"profile_id": "new_york", "name": "New York Accent", "language": "en", "method": "zero_shot", "is_default": True}
    ]

    def fake_generate(text: str, voice_profile: str = "new_york") -> np.ndarray:
        duration = max(len(text.split()) * 0.3, 1.0)
        n = int(duration * engine.SAMPLE_RATE)
        return (np.sin(np.linspace(0, 2 * np.pi * 440, n)) * 0.3).astype(np.float32)

    engine.generate.side_effect = fake_generate

    def fake_generate_stream(text, voice_profile="new_york", chunk_size_ms=200):
        full = fake_generate(text, voice_profile)
        chunk_len = int(engine.SAMPLE_RATE * chunk_size_ms / 1000)
        for i in range(0, len(full), chunk_len):
            yield full[i : i + chunk_len]

    engine.generate_stream.side_effect = fake_generate_stream
    set_tts_engine(engine)
    return engine


@pytest.fixture
def mock_aligner():
    """Mock phoneme aligner returning canned alignment."""
    from core.phoneme_aligner import Wav2Vec2Aligner, set_aligner

    engine = MagicMock(spec=Wav2Vec2Aligner)
    engine.is_loaded.return_value = True

    def fake_align(audio, text, sample_rate=16000):
        words = text.lower().split()
        phonemes = []
        t = 0.0
        for word in words:
            for ph, dur in [("ð", 0.08), ("ɪ", 0.08), ("s", 0.08)]:
                phonemes.append({
                    "phoneme": ph,
                    "start": round(t, 3),
                    "end": round(t + dur, 3),
                    "confidence": 0.85,
                    "difficulty": 0.5,
                })
                t += dur
        return phonemes

    engine.align.side_effect = fake_align
    engine.arpabet_to_ipa.side_effect = lambda x: x.lower()
    engine.phoneme_difficulty.return_value = 0.5

    set_aligner(engine)
    return engine


@pytest.fixture
def mock_llm_client():
    """Mock LLM client returning canned responses."""
    from llm.cloud import CloudLLMClient, set_llm_client

    client = MagicMock(spec=CloudLLMClient)
    client.is_available.return_value = True
    client.chat.return_value = "That sounds like a great plan! Let's do it."
    client.model = "gpt-4o-mini"
    set_llm_client(client)
    return client


# ── FastAPI TestClient fixture ──────────────────────────────────


@pytest.fixture
def client(
    mock_stt_engine,
    mock_tts_engine,
    mock_aligner,
    mock_llm_client,
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with all engine mocks wired."""
    # Import here so mocks are in place before module-level code runs
    from server import app

    with TestClient(app) as c:
        yield c


# ── session fixture ─────────────────────────────────────────────


@pytest.fixture
def active_session(sample_session_id):
    """Create and return an active session."""
    from core.session_manager import session_manager

    session = session_manager.create_session(session_id=sample_session_id)
    yield session
    session_manager.remove_session(sample_session_id)
