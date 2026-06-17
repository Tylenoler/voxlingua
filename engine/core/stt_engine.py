"""
Whisper STT Engine — Speech-to-Text using OpenAI Whisper.

Supports:
  - Local inference with configurable model size (tiny → large)
  - GPU (CUDA) / CPU auto-detection
  - Language detection and forced-language mode
  - Word-level timestamps for phoneme alignment
  - Graceful degradation when model is unavailable

Usage:
    engine = WhisperSTTEngine(model_size="small", device="cuda")
    engine.load()
    result = engine.transcribe(audio_array, language="en")
    # result["text"]       → "I think this is a good idea."
    # result["segments"]   → [{"start": 0.0, "end": 1.2, "text": "I think ..."}]
"""

import os
import time
import logging
import threading
from typing import Optional, Any

import numpy as np

logger = logging.getLogger("voxlingua.stt_engine")


class WhisperSTTEngine:
    """Speech-to-text engine wrapping OpenAI Whisper local model.

    Thread-safe: internal lock serialises access to the model.
    """

    # Model → approximate VRAM usage
    MODEL_MEMORY_MIB = {
        "tiny": 1000,
        "base": 1500,
        "small": 2500,
        "medium": 5000,
        "large": 10000,
    }

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        if model_size not in self.MODEL_MEMORY_MIB:
            raise ValueError(
                f"Unknown model size '{model_size}'. "
                f"Choose from: {list(self.MODEL_MEMORY_MIB.keys())}"
            )
        self.model_size = model_size

        if device == "cuda" and not self._cuda_available():
            logger.warning("CUDA not available, falling back to CPU")
            device = "cpu"
        self.device = device

        # float16 is only meaningful on CUDA
        self.compute_type = compute_type if device == "cuda" else "default"

        self._model: Any = None
        self._loaded = False
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    # ── public API ────────────────────────────────────────────────

    def load(self) -> bool:
        """Load the Whisper model. Returns ``True`` on success."""
        if self._loaded:
            return True

        with self._load_lock:
            if self._loaded:  # double-check after acquiring lock
                return True

            try:
                import whisper

                logger.info(
                    "Loading Whisper model '%s' on %s …",
                    self.model_size,
                    self.device,
                )
                start = time.perf_counter()

                self._model = whisper.load_model(
                    self.model_size,
                    device=self.device,
                )

                elapsed = time.perf_counter() - start
                # Check if the model was downloaded (first load includes download)
                cache_dir = os.path.expanduser(
                    os.path.join("~", ".cache", "whisper")
                )
                if os.path.isdir(cache_dir):
                    logger.info(
                        "Whisper model cache: %s (%.1f MiB)",
                        cache_dir,
                        self._dir_size_mib(cache_dir),
                    )

                logger.info(
                    "Whisper model '%s' loaded in %.1f s",
                    self.model_size,
                    elapsed,
                )
                self._loaded = True
                return True

            except ImportError as exc:
                logger.error(
                    "whisper package not installed. "
                    "Run: pip install openai-whisper.  Detail: %s",
                    exc,
                )
                return False
            except Exception as exc:
                logger.error(
                    "Failed to load Whisper model '%s': %s",
                    self.model_size,
                    exc,
                )
                return False

    def is_loaded(self) -> bool:
        return self._loaded

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en",
        word_timestamps: bool = True,
    ) -> dict:
        """Transcribe *audio* to text.

        Parameters
        ----------
        audio : np.ndarray
            1-D float32 array of audio samples (any sample rate — Whisper
            internally resamples to 16 kHz).
        language : str
            ISO 639-1 language code (e.g. ``"en"``, ``"zh"``).  Set to
            ``None`` for auto-detect.
        word_timestamps : bool
            Whether to include word-level timing in segments.

        Returns
        -------
        dict with keys:
            text       : str  — full transcription
            language   : str  — detected or forced language code
            segments   : list[dict] — each with ``start``, ``end``, ``text``,
                          and optionally ``words`` (if *word_timestamps*)
            duration   : float — audio duration in seconds
        """
        if not self._loaded:
            raise RuntimeError("STT engine not initialised – call .load() first")

        if len(audio) == 0:
            logger.warning("transcribe() called with empty audio")
            return {"text": "", "language": language, "segments": [], "duration": 0.0}

        duration = len(audio) / 16000  # approximate (Whisper resamples internally)
        logger.debug(
            "Transcribing %.1f s of audio (lang=%s, word_timestamps=%s) …",
            duration,
            language,
            word_timestamps,
        )

        with self._infer_lock:
            try:
                decode_options = {
                    "language": language,
                    "task": "transcribe",
                    "without_timestamps": False,
                }
                result = self._model.transcribe(
                    audio,
                    **decode_options,
                    word_timestamps=word_timestamps,
                )
            except Exception as exc:
                logger.error("Whisper transcription failed: %s", exc)
                return {
                    "text": "",
                    "language": language or "unknown",
                    "segments": [],
                    "duration": duration,
                    "error": str(exc),
                }

        text = (result.get("text") or "").strip()
        detected_lang = result.get("language", language or "unknown")
        segments_raw = result.get("segments", [])

        segments = []
        for seg in segments_raw:
            entry = {
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "text": (seg.get("text") or "").strip(),
            }
            if word_timestamps and "words" in seg:
                entry["words"] = [
                    {
                        "word": w.get("word", "").strip(),
                        "start": float(w.get("start", 0)),
                        "end": float(w.get("end", 0)),
                        "probability": float(w.get("probability", 0)),
                    }
                    for w in seg["words"]
                    if w.get("word", "").strip()
                ]
            segments.append(entry)

        logger.info(
            "Transcribed %.1f s → %d chars, %d segments (lang=%s)",
            duration,
            len(text),
            len(segments),
            detected_lang,
        )

        return {
            "text": text,
            "language": detected_lang,
            "segments": segments,
            "duration": duration,
        }

    def unload(self) -> None:
        """Release model memory."""
        self._model = None
        self._loaded = False
        if self.device == "cuda":
            import torch
            torch.cuda.empty_cache()
        logger.info("STT engine unloaded")

    # ── internal helpers ──────────────────────────────────────────

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    @staticmethod
    def _dir_size_mib(path: str) -> float:
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return total / (1024 * 1024)


# ── Module-level singleton (same pattern as tts_engine / llm / cloud) ─

_stt_engine: Optional[WhisperSTTEngine] = None


def get_stt_engine() -> WhisperSTTEngine:
    """Return the global STT engine instance.

    Raises ``RuntimeError`` if ``set_stt_engine()`` has not been called.
    """
    if _stt_engine is None:
        raise RuntimeError("STT engine not initialised")
    return _stt_engine


def set_stt_engine(engine: WhisperSTTEngine) -> None:
    """Set the global STT engine instance (called at server startup)."""
    global _stt_engine
    _stt_engine = engine


__all__ = [
    "WhisperSTTEngine",
    "get_stt_engine",
    "set_stt_engine",
]
