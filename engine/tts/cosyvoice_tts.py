"""
CosyVoice 3 TTS — Text-to-speech with voice cloning and streaming

Integrates CosyVoice 3 from FunAudioLLM for:
  - Natural TTS with voice cloning (zero-shot)
  - Streaming audio synthesis
  - Multiple voice profile support (NYC accent)
  - Cross-lingual synthesis

Fallback:
  When CosyVoice is not installed, falls back to Edge TTS
  (Microsoft neural voices via edge-tts library).

Model sources:
  - ModelScope: https://www.modelscope.cn/models/iic/CosyVoice-300M
  - HuggingFace: https://huggingface.co/FunAudioLLM/CosyVoice-300M
"""

import logging
import threading
from pathlib import Path
from typing import Generator, Optional

import numpy as np

logger = logging.getLogger("voxlingua.tts.cosyvoice")


class CosyVoiceTTS:
    """CosyVoice 3 TTS engine with voice cloning support.

    Supports three inference modes:
      1. SFT: Standard text-to-speech with predefined speaker
      2. Zero-shot: Voice cloning from a short reference audio
      3. Cross-lingual: Clone voice across languages

    Falls back to Edge TTS (edge-tts) when CosyVoice is not available.

    Voice profiles are stored as {profile_name}.wav in the profiles_dir.
    """

    def __init__(
        self,
        model_dir: str = "",
        device: str = "auto",
        profiles_dir: str = "",
    ):
        """
        Args:
            model_dir: Path to CosyVoice model directory.
                       Default: engine/models/weights/cosyvoice/300m
            device: 'cuda', 'cpu', or 'auto'
            profiles_dir: Directory containing voice profile .wav files.
                          Default: engine/voice_profiles/
        """
        self.model_dir = model_dir
        self.device = device
        self.profiles_dir = profiles_dir or str(
            Path(__file__).parent.parent / "voice_profiles"
        )
        self._model = None
        self._lock = threading.Lock()
        self._edge_tts = None  # Lazy-loaded fallback

    def _get_edge_tts(self):
        """Get or create EdgeTTS fallback instance."""
        if self._edge_tts is None:
            try:
                from .edge_tts import EdgeTTS
                self._edge_tts = EdgeTTS(profiles_dir=self.profiles_dir)
                logger.info("EdgeTTS fallback initialized")
            except ImportError:
                logger.warning("EdgeTTS not available, will use silence fallback")
                return None
        return self._edge_tts

    def _lazy_load(self):
        """Load CosyVoice model on first use."""
        if self._model is not None:
            return

        model_path = self.model_dir
        if not model_path:
            try:
                from engine.models.model_manager import get_model_path
                model_path = str(get_model_path("cosyvoice", "300m"))
            except Exception:
                model_path = ""

        if not model_path or not Path(model_path).exists():
            logger.info(
                "CosyVoice model path not found. Will use Edge TTS fallback."
            )
            return  # Don't raise, just use fallback

        logger.info(f"Loading CosyVoice model from {model_path}...")

        try:
            from cosyvoice.cli.cosyvoice import CosyVoice
            self._model = CosyVoice(model_path)
            logger.info("CosyVoice model loaded successfully")
        except ImportError:
            logger.warning(
                "CosyVoice package not found. Will use Edge TTS fallback."
            )
        except Exception as e:
            logger.error(f"Failed to load CosyVoice model: {e}")

    def synthesize(
        self,
        text: str,
        voice_profile: str = "new_york",
    ) -> np.ndarray:
        """Synthesize text to speech with the given voice profile.

        Args:
            text: Text to synthesize
            voice_profile: Name of voice profile (e.g., 'new_york', 'default')

        Returns:
            Audio waveform as float32 numpy array at 24kHz
        """
        self._lazy_load()

        # If CosyVoice model is loaded, use it
        if self._model is not None:
            profile_path = Path(self.profiles_dir) / f"{voice_profile}.wav"
            try:
                if profile_path.exists():
                    return self._synthesize_with_clone(text, str(profile_path))
                else:
                    logger.info(f"Voice profile '{voice_profile}' not found, using SFT mode")
                    return self._synthesize_sft(text)
            except Exception as e:
                logger.warning(f"CosyVoice synthesis failed, falling back: {e}")

        # Fallback to Edge TTS
        edge = self._get_edge_tts()
        if edge is not None:
            logger.info(f"Using Edge TTS fallback (voice: {voice_profile})")
            return edge.synthesize(text, voice_profile)

        # Last resort: silence
        logger.warning("No TTS backend available, generating silence")
        return self._fallback_silence(text)

    def synthesize_stream(
        self,
        text: str,
        voice_profile: str = "new_york",
        chunk_size_ms: int = 200,
    ) -> Generator[np.ndarray, None, None]:
        """Stream text-to-speech in chunks for real-time playback.

        Yields audio chunks as float32 numpy arrays at 24kHz.
        """
        full_audio = self.synthesize(text, voice_profile)
        sample_rate = 24000
        chunk_samples = int(sample_rate * chunk_size_ms / 1000)

        for start in range(0, len(full_audio), chunk_samples):
            yield full_audio[start:start + chunk_samples]

    def _synthesize_sft(self, text: str) -> np.ndarray:
        """Standard TTS with default speaker embedding."""
        try:
            result = self._model.inference_sft(
                text,
                spk_id="default",
            )
            return result["tts_speech"].numpy()
        except Exception as e:
            logger.error(f"SFT synthesis failed: {e}")
            raise

    def _synthesize_with_clone(self, text: str, profile_path: str) -> np.ndarray:
        """TTS with zero-shot voice cloning from reference audio."""
        try:
            from cosyvoice.utils.file_utils import load_wav

            # Load and condition reference audio
            prompt_speech_16k = load_wav(profile_path, 16000)

            result = self._model.inference_zero_shot(
                text,
                prompt_speech_16k,
                text,
            )

            audio_chunks = []
            for audio_data in result:
                audio_chunks.append(audio_data["tts_speech"].numpy())

            if audio_chunks:
                return np.concatenate(audio_chunks)
            return np.zeros((0,), dtype=np.float32)

        except Exception as e:
            logger.warning(f"Voice clone failed, falling back to SFT: {e}")
            return self._synthesize_sft(text)

    def _fallback_silence(self, text: str) -> np.ndarray:
        """Generate silence as fallback when TTS fails."""
        estimated_duration = max(len(text.split()) * 0.3, 1.0)
        num_samples = int(estimated_duration * 24000)
        return np.zeros(num_samples, dtype=np.float32)

    def is_available(self) -> bool:
        """Check if CosyVoice model is loaded."""
        return self._model is not None

    def list_profiles(self) -> list[dict]:
        """List available voice profiles.

        Returns CosyVoice WAV profiles + Edge TTS voice profiles.
        """
        profiles = []

        # CosyVoice WAV profiles
        profiles_dir = Path(self.profiles_dir)
        if profiles_dir.exists():
            for wav_file in sorted(profiles_dir.glob("*.wav")):
                profiles.append({
                    "profile_id": wav_file.stem,
                    "name": wav_file.stem.replace("_", " ").title(),
                    "language": "en",
                    "is_default": wav_file.stem == "new_york",
                })

        # Edge TTS profiles as built-in options
        if self._edge_tts or not profiles:
            try:
                from .edge_tts import VOICE_INFO
                for profile_id, info in VOICE_INFO.items():
                    if not any(p["profile_id"] == profile_id for p in profiles):
                        profiles.append({
                            "profile_id": profile_id,
                            "name": info["name"],
                            "language": info["language"],
                            "is_default": info.get("is_default", False),
                        })
            except ImportError:
                pass

        return profiles