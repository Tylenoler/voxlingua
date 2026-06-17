"""
Tests for core/audio_processor.py — encode, decode, chunk utilities.
"""

import base64
from io import BytesIO

import numpy as np
import pytest

from core.audio_processor import (
    decode_base64_audio,
    encode_pcm_f32le,
    encode_wav,
    chunk_audio,
    audio_duration,
    normalize_audio,
)


class TestEncodePcmF32le:
    def test_roundtrip(self):
        """encode_pcm_f32le → decode_base64_audio preserves content."""
        original = np.array([0.5, -0.5, 0.0, 0.25], dtype=np.float32)
        encoded = encode_pcm_f32le(original, 16000)
        decoded = decode_base64_audio(encoded, 16000)
        assert np.allclose(original, decoded, atol=1e-6)

    def test_output_is_base64(self):
        audio = np.zeros(100, dtype=np.float32)
        encoded = encode_pcm_f32le(audio, 16000)
        # verify it's valid base64
        decoded_bytes = base64.b64decode(encoded)
        assert len(decoded_bytes) == 100 * 4  # float32 = 4 bytes

    def test_empty_audio(self):
        audio = np.array([], dtype=np.float32)
        encoded = encode_pcm_f32le(audio, 16000)
        assert encoded == ""


class TestDecodeBase64Audio:
    def test_resampling(self):
        """24 kHz → decode_base64_audio at 16 kHz should change length."""
        sr = 24000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        buf = BytesIO()
        import soundfile as sf
        sf.write(buf, audio, sr, format="WAV")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        decoded = decode_base64_audio(b64, target_sr=16000)
        assert len(decoded) < len(audio)  # resampled down
        assert decoded.dtype == np.float32

    def test_invalid_base64(self):
        with pytest.raises(Exception):
            decode_base64_audio("!!!invalid!!!", 16000)


class TestEncodeWav:
    def test_roundtrip(self):
        audio = np.array([0.3, -0.3, 0.1], dtype=np.float32)
        encoded = encode_wav(audio, 16000)
        decoded = decode_base64_audio(encoded, 16000)
        assert len(decoded) > 0

    def test_has_wav_header(self):
        audio = np.zeros(100, dtype=np.float32)
        encoded = encode_wav(audio, 16000)
        raw = base64.b64decode(encoded)
        # WAV header starts with "RIFF"
        assert raw[:4] == b"RIFF"


class TestChunkAudio:
    @pytest.fixture
    def audio(self):
        return np.ones(16000, dtype=np.float32)  # 1s at 16 kHz

    def test_chunk_count(self, audio):
        chunks = chunk_audio(audio, chunk_size_ms=200, sample_rate=16000)
        assert len(chunks) == 5  # 5 × 200 ms = 1 s

    def test_chunk_size(self, audio):
        chunks = chunk_audio(audio, chunk_size_ms=200, sample_rate=16000)
        for c in chunks[:-1]:
            assert len(c) == 3200  # 200 ms × 16 Hz → 3200 samples
        # last chunk may be shorter
        assert len(chunks[-1]) <= 3200

    def test_uneven_division(self):
        audio = np.ones(8000, dtype=np.float32)  # 500 ms at 16 kHz
        chunks = chunk_audio(audio, chunk_size_ms=300, sample_rate=16000)
        # 300 ms = 4800 samples, 2 chunks: 4800 + 3200
        assert len(chunks) == 2
        assert len(chunks[0]) == 4800
        assert len(chunks[1]) == 3200

    def test_empty_audio(self):
        chunks = chunk_audio(np.array([], dtype=np.float32))
        assert chunks == []

    def test_small_audio_single_chunk(self):
        audio = np.ones(100, dtype=np.float32)
        chunks = chunk_audio(audio, chunk_size_ms=200, sample_rate=16000)
        assert len(chunks) == 1
        assert len(chunks[0]) == 100


class TestAudioDuration:
    def test_duration(self):
        audio = np.zeros(16000, dtype=np.float32)
        assert audio_duration(audio, 16000) == 1.0

    def test_half_second(self):
        audio = np.zeros(8000, dtype=np.float32)
        assert audio_duration(audio, 16000) == 0.5

    def test_empty(self):
        assert audio_duration(np.array([]), 16000) == 0.0


class TestNormalizeAudio:
    def test_normalize_peak(self):
        audio = np.array([0.5, -0.5, 0.25], dtype=np.float32)
        normalized = normalize_audio(audio)
        assert np.max(np.abs(normalized)) == pytest.approx(1.0, abs=1e-6)

    def test_already_normalized(self):
        audio = np.array([1.0, -0.5, 0.0], dtype=np.float32)
        normalized = normalize_audio(audio)
        assert np.max(np.abs(normalized)) == 1.0

    def test_silence(self):
        audio = np.zeros(100, dtype=np.float32)
        normalized = normalize_audio(audio)
        assert np.all(normalized == 0.0)
