# VoxLingua TTS Module
#
# Text-to-speech with multiple backends:
#   - Edge TTS (default, always available, Microsoft neural voices)
#   - CosyVoice 3 (optional, voice cloning + streaming)

from .cosyvoice_tts import CosyVoiceTTS
from .edge_tts import EdgeTTS

__all__ = ["CosyVoiceTTS", "EdgeTTS"]