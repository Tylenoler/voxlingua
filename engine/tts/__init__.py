# VoxLingua TTS Module
#
# Text-to-speech with voice cloning:
#   CosyVoice 3 (SFT + zero-shot voice cloning + streaming)

from .cosyvoice_tts import CosyVoiceTTS

__all__ = ["CosyVoiceTTS"]
