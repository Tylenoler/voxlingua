"""
CosyVoice TTS Engine — Text-to-Speech synthesis using CosyVoice 2/3.

Supports:
  - Zero-shot voice cloning from reference audio (voice profiles)
  - SFT mode with pre-registered speakers
  - Full audio generation for pipeline consumption
  - Graceful degradation when model is unavailable

Usage:
    engine = CosyVoiceEngine(model_dir="./models/cosyvoice", device="cuda")
    engine.load()
    audio = engine.generate("Hello, how are you?", voice_profile="new_york")
    # audio is np.ndarray of PCM f32le at 24 kHz
"""

import os
import time
import logging
import threading
from typing import Optional, Generator, Any

import numpy as np

logger = logging.getLogger("voxlingua.tts_engine")


class CosyVoiceEngine:
    """TTS engine wrapping CosyVoice 2/3 for local GPU/CPU inference.

    Two synthesis modes:
      - **Zero-shot**: clones a voice from a reference audio sample.
        Voice profiles are registered via ``add_zero_shot_spk()`` at load time.
      - **SFT**: uses a pre-registered speaker ID built into the model.

    Thread-safe: internal lock serialises access to the underlying model.
    """

    SAMPLE_RATE = 24000  # CosyVoice 2/3 output sample rate

    def __init__(
        self,
        model_dir: str,
        device: str = "cuda",
        fp16: bool = True,
        profiles_dir: Optional[str] = None,
    ):
        self.model_dir = os.path.abspath(model_dir)
        self.profiles_dir = os.path.abspath(profiles_dir) if profiles_dir else None

        # Resolve device
        if device == "cuda" and not self._cuda_available():
            logger.warning("CUDA not available, falling back to CPU")
            device = "cpu"
        self.device = device
        self.fp16 = fp16 and self.device == "cuda"

        self._model: Any = None
        self._loaded = False
        self._lock = threading.Lock()
        self._registered_profiles: set[str] = set()
        self._available_sft_speakers: list[str] = []

    # ── public API ────────────────────────────────────────────────

    def load(self) -> bool:
        """Load the CosyVoice model and register voice profiles.

        Returns ``True`` on success, ``False`` if the model directory is
        missing or loading fails.
        """
        if self._loaded:
            return True

        if not self._check_model_exists():
            logger.error(
                "CosyVoice model not found at '%s'. "
                "Run `python scripts/download_tts_model.py` to download it.",
                self.model_dir,
            )
            return False

        try:
            from cosyvoice.cli.cosyvoice import CosyVoice2

            logger.info("Loading CosyVoice model from %s …", self.model_dir)
            start = time.perf_counter()

            self._model = CosyVoice2(
                self.model_dir,
                load_jit=False,
                load_trt=False,
                fp16=self.fp16,
            )

            elapsed = time.perf_counter() - start
            logger.info("CosyVoice model loaded in %.1f s", elapsed)

            # Query built-in SFT speakers
            try:
                self._available_sft_speakers = self._model.list_avaliable_spks()
                logger.info("Available SFT speakers: %s", self._available_sft_speakers)
            except Exception:
                self._available_sft_speakers = []

            self._loaded = True
            self._register_profiles()
            return True

        except ImportError as exc:
            logger.error(
                "cosyvoice package not installed. "
                "Run: pip install cosyvoice  (or install from source). "
                "Detail: %s",
                exc,
            )
            return False
        except Exception as exc:
            logger.error("Failed to load CosyVoice model: %s", exc)
            return False

    def is_loaded(self) -> bool:
        return self._loaded

    def generate(self, text: str, voice_profile: str = "new_york") -> np.ndarray:
        """Synthesise *text* to speech.

        Returns a 1-D ``np.float32`` array of PCM samples at 24 kHz.

        Raises ``RuntimeError`` if the engine is not loaded.
        """
        if not self._loaded:
            raise RuntimeError("TTS engine not initialised – call .load() first")

        if not text.strip():
            logger.warning("generate() called with empty text – returning silence")
            return np.array([], dtype=np.float32)

        with self._lock:
            if voice_profile in self._registered_profiles:
                logger.debug("Zero-shot TTS with profile '%s'", voice_profile)
                return self._inference_zero_shot(text, voice_profile)

            # SFT fallback – use profile name as speaker ID if it exists,
            # otherwise use the first available speaker or "default".
            spk_id = (
                voice_profile
                if voice_profile in self._available_sft_speakers
                else (
                    self._available_sft_speakers[0]
                    if self._available_sft_speakers
                    else "default"
                )
            )
            logger.debug("SFT TTS with speaker '%s'", spk_id)
            return self._inference_sft(text, spk_id)

    def generate_stream(
        self,
        text: str,
        voice_profile: str = "new_york",
        chunk_size_ms: int = 200,
    ) -> Generator[np.ndarray, None, None]:
        """Synthesise and yield audio chunks for streaming.

        Each chunk is a 1-D ``np.float32`` array of roughly *chunk_size_ms*
        milliseconds at 24 kHz.
        """
        full = self.generate(text, voice_profile)
        chunk_len = int(self.SAMPLE_RATE * chunk_size_ms / 1000)
        for i in range(0, len(full), chunk_len):
            yield full[i : i + chunk_len]

    def unload(self) -> None:
        """Release GPU resources."""
        self._model = None
        self._loaded = False
        self._registered_profiles.clear()
        if self.device == "cuda":
            import torch

            torch.cuda.empty_cache()
        logger.info("TTS engine unloaded")

    def list_voices(self) -> list[dict]:
        """Return available voice profiles (both zero-shot and SFT)."""
        voices = []
        for pid in sorted(self._registered_profiles):
            voices.append({
                "profile_id": pid,
                "name": pid.replace("_", " ").title(),
                "language": "en",
                "method": "zero_shot",
                "is_default": pid == "new_york",
            })
        for spk in self._available_sft_speakers:
            if spk not in self._registered_profiles:
                voices.append({
                    "profile_id": spk,
                    "name": f"SFT: {spk}",
                    "language": "en" if "en" in spk.lower() else "zh",
                    "method": "sft",
                })
        return voices

    # ── internal helpers ──────────────────────────────────────────

    def _check_model_exists(self) -> bool:
        """Check whether the model directory contains a CosyVoice model."""
        # CosyVoice 2/3 models ship a ``model.yaml`` at root
        return os.path.isfile(os.path.join(self.model_dir, "model.yaml"))

    def _register_profiles(self) -> None:
        """Walk *profiles_dir* and register each as a zero-shot speaker."""
        if not self.profiles_dir or not os.path.isdir(self.profiles_dir):
            logger.info("No voice profiles directory at '%s'", self.profiles_dir)
            return

        for entry in sorted(os.listdir(self.profiles_dir)):
            profile_path = os.path.join(self.profiles_dir, entry)
            if not os.path.isdir(profile_path):
                continue

            ref_audio = os.path.join(profile_path, "reference.wav")
            ref_text = os.path.join(profile_path, "reference.txt")

            if not (os.path.isfile(ref_audio) and os.path.isfile(ref_text)):
                logger.warning(
                    "Voice profile '%s' missing reference.wav or reference.txt – skipping",
                    entry,
                )
                continue

            try:
                prompt_text = self._read_prompt_text(ref_text)
                self._model.add_zero_shot_spk(
                    entry,
                    prompt_wav=ref_audio,
                    prompt_text=prompt_text,
                )
                self._registered_profiles.add(entry)
                logger.info("Registered voice profile: %s", entry)
            except Exception as exc:
                logger.error("Failed to register voice profile '%s': %s", entry, exc)

    def _inference_sft(self, text: str, spk_id: str = "default") -> np.ndarray:
        """SFT mode – TTS with a pre-registered speaker embedding."""
        audio_parts: list[np.ndarray] = []
        assert self._model is not None, "Model not loaded"
        try:
            for result in self._model.inference_sft(tts_text=text, spk_id=spk_id):
                audio_parts.append(result["tts_speech"].cpu().numpy())
        except Exception as exc:
            logger.error("SFT inference failed: %s", exc)
            return np.array([], dtype=np.float32)

        if not audio_parts:
            return np.array([], dtype=np.float32)
        return np.concatenate(audio_parts, axis=1).squeeze(0)

    def _inference_zero_shot(self, text: str, profile_name: str) -> np.ndarray:
        """Zero-shot mode – TTS with a voice profile reference."""
        audio_parts: list[np.ndarray] = []
        assert self._model is not None, "Model not loaded"
        try:
            for result in self._model.inference_zero_shot(
                tts_text=text,
                zero_shot_spk_id=profile_name,
            ):
                audio_parts.append(result["tts_speech"].cpu().numpy())
        except Exception as exc:
            logger.error("Zero-shot inference failed for '%s': %s", profile_name, exc)
            return np.array([], dtype=np.float32)

        if not audio_parts:
            return np.array([], dtype=np.float32)
        return np.concatenate(audio_parts, axis=1).squeeze(0)

    @staticmethod
    def _read_prompt_text(path: str) -> str:
        """Read prompt text from a UTF-8 text file, stripping whitespace."""
        with open(path, encoding="utf-8") as f:
            return f.read().strip()

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False


# ── Module-level singleton (same pattern as llm/cloud.py) ─────────

_tts_engine: Optional[CosyVoiceEngine] = None


def get_tts_engine() -> CosyVoiceEngine:
    """Return the global TTS engine instance.

    Raises ``RuntimeError`` if ``set_tts_engine()`` has not been called.
    """
    if _tts_engine is None:
        raise RuntimeError("TTS engine not initialised")
    return _tts_engine


def set_tts_engine(engine: CosyVoiceEngine) -> None:
    """Set the global TTS engine instance (called at server startup)."""
    global _tts_engine
    _tts_engine = engine


__all__ = [
    "CosyVoiceEngine",
    "get_tts_engine",
    "set_tts_engine",
]
