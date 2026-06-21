# VoxLingua STT Module
#
# Speech-to-text with phoneme-level analysis pipeline:
#   Whisper (transcription + word timestamps)
#   → Wav2Vec2 (phoneme CTC alignment)
#   → Prosody analysis (pitch, energy, speaking rate)

from .whisper_stt import WhisperSTT

__all__ = ["WhisperSTT"]
