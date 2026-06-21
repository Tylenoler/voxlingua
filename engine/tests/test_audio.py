"""Tests for audio processor."""

import sys; sys.path.insert(0, ".")
import numpy as np
from core.audio_processor import (
    decode_base64_audio,
    encode_pcm_f32le,
    encode_wav,
    chunk_audio,
    normalize_audio,
)


def test_encode_decode_roundtrip():
    audio = np.sin(np.linspace(0, 2*np.pi*440, 16000)).astype(np.float32) * 0.5
    encoded = encode_pcm_f32le(audio, 16000)
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    decoded = decode_base64_audio(encoded, 16000)
    assert np.allclose(audio, decoded, atol=1e-6)
    print(f"  Roundtrip: {len(audio)} samples -> {len(encoded)} chars -> {len(decoded)} samples")
    return True


def test_encode_wav():
    audio = np.zeros(8000, dtype=np.float32)
    encoded = encode_wav(audio, 16000)
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    return True


def test_chunk_audio():
    audio = np.ones(48000, dtype=np.float32)
    chunks = chunk_audio(audio, chunk_size_ms=200, sample_rate=24000)
    assert len(chunks) == 10
    for c in chunks:
        assert len(c) == 4800
    return True


def test_normalize_audio():
    audio = np.array([0.5, -0.5, 0.0], dtype=np.float32)
    normed = normalize_audio(audio)
    assert np.max(np.abs(normed)) <= 1.0
    return True


def test_dtype_param():
    audio = np.zeros(1600, dtype=np.float32)
    encoded = encode_pcm_f32le(audio, 16000)
    decoded_f32 = decode_base64_audio(encoded, 16000, dtype=np.float32)
    decoded_f64 = decode_base64_audio(encoded, 16000, dtype=np.float64)
    assert decoded_f32.dtype == np.float32
    assert decoded_f64.dtype == np.float64
    return True


if __name__ == "__main__":
    print("test_encode_decode_roundtrip...", end=" ")
    assert test_encode_decode_roundtrip()
    print("PASS")
    
    print("test_encode_wav...", end=" ")
    assert test_encode_wav()
    print("PASS")
    
    print("test_chunk_audio...", end=" ")
    assert test_chunk_audio()
    print("PASS")
    
    print("test_normalize_audio...", end=" ")
    assert test_normalize_audio()
    print("PASS")
    
    print("test_dtype_param...", end=" ")
    assert test_dtype_param()
    print("PASS")
    
    print("\n=== ALL AUDIO TESTS PASSED ===")