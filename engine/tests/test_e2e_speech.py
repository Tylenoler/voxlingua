"""E2E test: model manager + pipeline structure."""

import sys; sys.path.insert(0, ".")
import numpy as np
from stt.whisper_stt import WhisperSTT
from core.correction_engine import CorrectionEngine
from models.model_manager import is_model_downloaded, get_model_path


def test_model_manager():
    assert is_model_downloaded("wav2vec2", "base")
    path = get_model_path("wav2vec2", "base")
    assert path.exists()
    print(f"OK: Wav2Vec2 base at {path}")
    
    # CosyVoice may be downloaded (if setup is run)
    downloaded = is_model_downloaded("cosyvoice", "300m"); print(f"OK: CosyVoice downloaded: {downloaded}")
    return True


def test_stt_with_real_noise():
    """STT with noise signal (realistic non-speech)."""
    stt = WhisperSTT(model_size="tiny", device="cpu")
    engine = CorrectionEngine()

    # Brown noise + tonal components (more speech-like)
    t = np.linspace(0, 2.0, int(16000*2), endpoint=False)
    noise = np.cumsum(np.random.randn(len(t)) * 0.02)
    noise = noise / np.max(np.abs(noise)) * 0.3
    tones = 0.15 * np.sin(2*np.pi*180*t) + 0.1 * np.sin(2*np.pi*280*t)
    audio = (noise + tones).astype(np.float32)

    stt_result = stt.transcribe_with_phonemes(audio)
    print(f"STT text: [{stt_result['text']}]")
    print(f"Phonemes: {len(stt_result['phonemes'])}")
    print(f"Prosody: {stt_result['prosody']}")

    result = engine.process(
        audio=audio,
        user_text=stt_result["text"] or "test audio",
        target_text="test audio signal",
        user_phonemes=stt_result["phonemes"],
        prosody=stt_result["prosody"],
    )
    print(f"Correction: level={result.level}, score={result.overall_score}")
    assert result.level in ("mild", "medium", "severe")
    assert 0 <= result.overall_score <= 100
    print("OK: Pipeline structure verified")
    return True


if __name__ == "__main__":
    test_model_manager()
    test_stt_with_real_noise()
    print("\n=== ALL E2E TESTS PASSED ===")