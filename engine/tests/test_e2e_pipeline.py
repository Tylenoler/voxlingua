"""End-to-end pipeline test: STT -> Correction."""

import sys; sys.path.insert(0, ".")
import numpy as np
from stt.whisper_stt import WhisperSTT
from core.correction_engine import CorrectionEngine


def test_stt_and_correction():
    stt = WhisperSTT(model_size="tiny", device="cpu")
    engine = CorrectionEngine()

    t = np.linspace(0, 2.0, int(16000*2), endpoint=False)
    audio = (0.3 * np.sin(2 * np.pi * 200 * t) +
             0.15 * np.sin(2 * np.pi * 350 * t) +
             0.1 * np.random.randn(len(t))).astype(np.float32)

    stt_result = stt.transcribe_with_phonemes(audio)
    text = stt_result["text"]
    print(f"STT text: [{text}]")
    print(f"Prosody: {stt_result['prosody']}")

    result = engine.process(
        audio=audio,
        user_text=text,
        target_text="I think this is a good idea",
        user_phonemes=stt_result["phonemes"],
        prosody=stt_result["prosody"],
    )
    print(f"Correction: level={result.level}, score={result.overall_score}")
    for e in result.errors[:3]:
        print(f"  [{e.severity}] {e.phoneme} -> {e.actual}: {e.feedback}")
    
    assert result.level in ("mild", "medium", "severe")
    assert 0 <= result.overall_score <= 100
    print("OK: E2E pipeline test passed")
    return True


if __name__ == "__main__":
    test_stt_and_correction()