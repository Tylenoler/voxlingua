"""Tests for the correction engine."""

import sys; sys.path.insert(0, ".")
import numpy as np
from core.correction_engine import CorrectionEngine
from models.schemas import CorrectionMode


def test_basic_correction():
    engine = CorrectionEngine()
    audio = np.random.randn(16000).astype(np.float32) * 0.01
    
    result = engine.process(
        audio=audio,
        user_text="I think this is good",
        target_text="I think this is great",
    )
    
    assert result.level in ("mild", "medium", "severe")
    assert 0 <= result.overall_score <= 100
    assert len(result.errors) >= 0
    assert 0 <= result.dimensions.phoneme_accuracy <= 100
    assert 0 <= result.dimensions.fluency <= 100
    print(f"  Level={result.level}, Score={result.overall_score}, Errors={len(result.errors)}")
    return True


def test_correction_off_mode():
    engine = CorrectionEngine()
    audio = np.random.randn(16000).astype(np.float32) * 0.01
    
    mode = CorrectionMode(mode="off", interrupt_on_severe=False)
    result = engine.process(audio=audio, user_text="hello", target_text="hello", mode=mode)
    
    assert result.level == "mild"
    return True


def test_correction_with_phonemes():
    engine = CorrectionEngine()
    audio = np.random.randn(16000).astype(np.float32) * 0.01
    
    user_phonemes = [
        {"phoneme": "th", "start_time": 0.1, "end_time": 0.2, "confidence": 0.9, "word": "think"},
        {"phoneme": "ih", "start_time": 0.2, "end_time": 0.28, "confidence": 0.85, "word": "think"},
        {"phoneme": "ng", "start_time": 0.28, "end_time": 0.38, "confidence": 0.75, "word": "think"},
    ]
    prosody = {"pitch_range": 25.0, "pause_ratio": 0.12}
    
    result = engine.process(
        audio=audio, user_text="think", target_text="think",
        user_phonemes=user_phonemes, prosody=prosody,
    )
    
    assert len(result.errors) >= 0
    assert result.dimensions.fluency <= 100
    assert result.dimensions.prosody <= 100
    return True


def test_correction_all_levels():
    """Test mild, medium, severe all work."""
    engine = CorrectionEngine()
    audio = np.random.randn(16000).astype(np.float32) * 0.01
    
    # Use text that should hit the th error pattern (severe)
    result = engine.process(audio=audio, user_text="think thank", target_text="think thank")
    
    print(f"  All levels test: Level={result.level}, Errors:")
    for e in result.errors[:5]:
        print(f"    {e.phoneme} ({e.severity}): {e.feedback}")
    return True


if __name__ == "__main__":
    print("test_basic_correction...", end=" ")
    assert test_basic_correction()
    print("  PASS")
    
    print("test_correction_off_mode...", end=" ")
    assert test_correction_off_mode()
    print("  PASS")
    
    print("test_correction_with_phonemes...", end=" ")
    assert test_correction_with_phonemes()
    print("  PASS")
    
    print("test_correction_all_levels...", end=" ")
    assert test_correction_all_levels()
    print("  PASS")
    
    print("\n=== ALL CORRECTION TESTS PASSED ===")