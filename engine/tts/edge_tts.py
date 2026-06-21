"""
Edge TTS — Text-to-speech using Microsoft Edge's online TTS API

Provides high-quality neural TTS with multiple voice options.
Uses Microsoft's natural voices available through the Edge browser.

Features:
  - 40+ English voices (US, UK, AU, IN, etc.)
  - Neural TTS with natural prosody
  - SSML support for fine-grained control
  - Streaming support

Voice profiles map to specific Edge voices:
  - "new_york" -> en-US-JennyNeural (default, female)
  - "default"  -> en-US-JennyNeural
  - Custom profiles can be added in voice_profiles/
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("voxlingua.tts.edge")


# Edge TTS voice mapping for VoxLingua profiles
VOICE_MAP: dict[str, str] = {
    "new_york": "en-US-JennyNeural",
    "default": "en-US-JennyNeural",
    "us_female": "en-US-JennyNeural",
    "us_male": "en-US-BrianNeural",
    "uk_female": "en-GB-SoniaNeural",
    "uk_male": "en-GB-RyanNeural",
    "au_female": "en-AU-NatashaNeural",
    "au_male": "en-AU-WilliamMultilingualNeural",
}

# Additional information about each voice profile
VOICE_INFO: dict[str, dict] = {
    "new_york": {
        "name": "New York Accent (default)",
        "edge_voice": "en-US-JennyNeural",
        "language": "en",
        "is_default": True,
        "description": "Standard US English female voice",
    },
    "us_male": {
        "name": "US English Male",
        "edge_voice": "en-US-BrianNeural",
        "language": "en",
        "is_default": False,
        "description": "Standard US English male voice",
    },
    "uk_female": {
        "name": "UK English Female",
        "edge_voice": "en-GB-SoniaNeural",
        "language": "en",
        "is_default": False,
        "description": "British English female voice",
    },
    "uk_male": {
        "name": "UK English Male",
        "edge_voice": "en-GB-RyanNeural",
        "language": "en",
        "is_default": False,
        "description": "British English male voice",
    },
    "au_female": {
        "name": "Australian English Female",
        "edge_voice": "en-AU-NatashaNeural",
        "language": "en",
        "is_default": False,
        "description": "Australian English female voice",
    },
}


class EdgeTTS:
    """Text-to-speech using Microsoft Edge's TTS API.

    Uses the edge-tts library to synthesize speech with Microsoft's
    neural voices. Supports SSML and multiple voice profiles.

    This is a synchronous wrapper around the async edge-tts library.
    """

    def __init__(
        self,
        profiles_dir: str = "",
        default_voice: str = "new_york",
    ):
        """
        Args:
            profiles_dir: Directory for voice profile definitions (unused by edge-tts,
                          but kept for compatibility with CosyVoiceTTS interface)
            default_voice: Default voice profile to use
        """
        self.profiles_dir = profiles_dir or str(
            Path(__file__).parent.parent / "voice_profiles"
        )
        self.default_voice = default_voice
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create an event loop for async operations."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def _resolve_voice(self, voice_profile: str) -> str:
        """Resolve a voice profile name to an Edge TTS voice name."""
        voice = VOICE_MAP.get(voice_profile)
        if voice:
            return voice

        # If voice_profile is itself a valid edge-tts voice, use it directly
        return voice_profile

    def synthesize(
        self,
        text: str,
        voice_profile: str = "new_york",
    ) -> np.ndarray:
        """Synthesize text to speech using Edge TTS.

        Args:
            text: Text to synthesize
            voice_profile: Voice profile name (e.g., 'new_york', 'us_male', 'uk_female')

        Returns:
            Audio waveform as float32 numpy array at 24kHz
        """
        if not text.strip():
            logger.warning("Empty text for TTS synthesis")
            return np.zeros((0,), dtype=np.float32)

        voice = self._resolve_voice(voice_profile)
        logger.info(f"Synthesizing speech with Edge TTS, voice={voice}")

        try:
            loop = self._get_loop()
            audio_data = loop.run_until_complete(
                self._synthesize_async(text, voice)
            )
            return audio_data
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            return self._fallback_silence(text)

    async def _synthesize_async(self, text: str, voice: str) -> np.ndarray:
        """Async implementation of TTS synthesis."""
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)

        # Stream audio chunks and concatenate
        audio_chunks = []
        sample_rate = 24000

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        if not audio_chunks:
            logger.warning("No audio data received from Edge TTS")
            return self._fallback_silence(text)

        # Concatenate all audio bytes
        audio_bytes = b"".join(audio_chunks)

        # Decode MP3 to numpy array
        try:
            import io

            import soundfile as sf

            # edge-tts returns MP3 data, decode to PCM
            with io.BytesIO(audio_bytes) as f:
                data, orig_sr = sf.read(f)

            # Resample to 24kHz if needed
            if orig_sr != sample_rate:
                import librosa

                data = librosa.resample(
                    data.astype(np.float64),
                    orig_sr=orig_sr,
                    target_sr=sample_rate,
                ).astype(np.float32)

            # Ensure mono
            if data.ndim > 1:
                data = data.mean(axis=1)

            return data.astype(np.float32)

        except Exception as e:
            logger.warning(f"Failed to decode MP3 audio data: {e}")
            return self._fallback_silence(text)

    def synthesize_stream(
        self,
        text: str,
        voice_profile: str = "new_york",
        chunk_size_ms: int = 200,
    ):
        """Synthesize and yield audio chunks for streaming.

        Yields:
            np.ndarray audio chunks at 24kHz
        """
        full_audio = self.synthesize(text, voice_profile)
        sample_rate = 24000
        chunk_samples = int(sample_rate * chunk_size_ms / 1000)

        for start in range(0, len(full_audio), chunk_samples):
            yield full_audio[start:start + chunk_samples]

    def _fallback_silence(self, text: str) -> np.ndarray:
        """Generate silence as fallback when TTS fails."""
        estimated_duration = max(len(text.split()) * 0.3, 1.0)
        num_samples = int(estimated_duration * 24000)
        return np.zeros(num_samples, dtype=np.float32)

    def is_available(self) -> bool:
        """Check if Edge TTS is available (it always is once installed)."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    def list_profiles(self) -> list[dict]:
        """List available voice profiles."""
        profiles = []
        for profile_id, info in VOICE_INFO.items():
            profiles.append({
                "profile_id": profile_id,
                "name": info["name"],
                "language": info["language"],
                "is_default": info.get("is_default", False),
            })
        return profiles

    @staticmethod
    async def list_edge_voices(locale: str = "en") -> list[dict]:
        """List all available Edge TTS voices for a locale."""
        import edge_tts

        all_voices = await edge_tts.list_voices()
        return [
            {
                "name": v["FriendlyName"],
                "locale": v["Locale"],
                "gender": v["Gender"],
                "short_name": v["ShortName"],
            }
            for v in all_voices
            if v["Locale"].startswith(locale)
        ]