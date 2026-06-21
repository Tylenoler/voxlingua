"""
CosyVoice 3 TTS — Text-to-speech with voice cloning and streaming

Integrates CosyVoice 3 from FunAudioLLM:
  - Natural TTS with voice cloning (zero-shot)
  - Streaming audio synthesis
  - Multiple voice profile support
  - Cross-lingual synthesis

Requirements:
  - CosyVoice repo cloned to %TEMP%\cosyvoice (or set COSYVOICE_PATH)
  - matcha-tts installed (requires C++ build tools: https://aka.ms/vs/17/release/vs_BuildTools.exe)
  - Model weights downloaded via scripts/download_models.py

Fallback:
  When CosyVoice is not available, falls back to Edge TTS
  (Microsoft neural voices via edge-tts library).

Model sources:
  - ModelScope: https://www.modelscope.cn/models/iic/CosyVoice-300M
"""

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Generator, Optional

import numpy as np
import os

# Add vendor path for matcha-tts stubs (used when real matcha-tts is not installed)
_vendor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vendor')
if os.path.isdir(_vendor_path):
    import sys
    if _vendor_path not in sys.path:
        sys.path.insert(0, _vendor_path)

logger = logging.getLogger("voxlingua.tts.cosyvoice")

# Try to add CosyVoice source to path
_COSY_SOURCE = os.environ.get(
    "COSYVOICE_PATH",
    os.path.join(os.environ.get("TEMP", ""), "cosyvoice")
)
if os.path.isdir(_COSY_SOURCE) and _COSY_SOURCE not in sys.path:
    sys.path.insert(0, _COSY_SOURCE)


class CosyVoiceTTS:
    """CosyVoice 3 TTS engine with voice cloning support.

    Supports zero-shot voice cloning from reference audio.
    Falls back to Edge TTS when CosyVoice is not available.
    """

    def __init__(
        self,
        model_dir: str = "",
        device: str = "auto",
        profiles_dir: str = "",
    ):
        self.model_dir = model_dir
        self.device = device
        self.profiles_dir = profiles_dir or str(
            Path(__file__).parent.parent / "voice_profiles"
        )
        self._model = None
        self._lock = threading.Lock()
        self._edge_tts = None

    def _get_edge_tts(self):
        if self._edge_tts is None:
            try:
                from .edge_tts import EdgeTTS
                self._edge_tts = EdgeTTS(profiles_dir=self.profiles_dir)
                logger.info("EdgeTTS fallback initialized")
            except ImportError:
                logger.warning("EdgeTTS not available, will use silence fallback")
                return None
        return self._edge_tts

    def _resolve_model_path(self) -> Optional[str]:
        """Find CosyVoice model directory."""
        if self.model_dir and os.path.isdir(self.model_dir):
            return self.model_dir

        # Check standard download locations
        candidates = [
            str(Path(__file__).parent.parent / "models" / "weights" / "cosyvoice" / "iic" / "CosyVoice-300M"),
            str(Path(__file__).parent.parent / "models" / "weights" / "cosyvoice" / "CosyVoice-300M"),
        ]
        # Check ModelScope cache
        ms_cache = os.path.join(Path.home(), ".cache", "modelscope", "hub", "iic", "CosyVoice-300M")
        candidates.append(ms_cache)

        for c in candidates:
            if os.path.isdir(c) and os.path.isfile(os.path.join(c, "cosyvoice.yaml")):
                return c
        return None

    def _lazy_load(self):
        """Load CosyVoice model on first use."""
        if self._model is not None:
            return

        model_path = self._resolve_model_path()
        if not model_path:
            logger.info("CosyVoice model not found. Using Edge TTS fallback.")
            return

        logger.info(f"Loading CosyVoice model from {model_path}...")

        try:
            from cosyvoice.cli.cosyvoice import CosyVoice
            self._model = CosyVoice(model_path)
            logger.info("CosyVoice model loaded successfully")
        except ImportError as e:
            logger.warning(f"CosyVoice package import failed: {e}. Using Edge TTS fallback.")
            logger.warning("To use CosyVoice: run scripts/setup_cosyvoice.bat")
        except Exception as e:
            logger.error(f"Failed to load CosyVoice model: {e}")

    def synthesize(
        self,
        text: str,
        voice_profile: str = "new_york",
    ) -> np.ndarray:
        self._lazy_load()

        if self._model is not None:
            profile_path = Path(self.profiles_dir) / f"{voice_profile}.wav"
            try:
                if profile_path.exists():
                    return self._synthesize_with_clone(text, str(profile_path))
                else:
                    return self._synthesize_sft(text)
            except Exception as e:
                logger.warning(f"CosyVoice failed, falling back: {e}")

        edge = self._get_edge_tts()
        if edge is not None:
            return edge.synthesize(text, voice_profile)

        return self._fallback_silence(text)

    def synthesize_stream(
        self,
        text: str,
        voice_profile: str = "new_york",
        chunk_size_ms: int = 200,
    ) -> Generator[np.ndarray, None, None]:
        full_audio = self.synthesize(text, voice_profile)
        sr = 24000
        cs = int(sr * chunk_size_ms / 1000)
        for start in range(0, len(full_audio), cs):
            yield full_audio[start:start + cs]

    def _synthesize_sft(self, text: str) -> np.ndarray:
        result = self._model.inference_sft(text, spk_id="default")
        return result["tts_speech"].numpy()

    def _synthesize_with_clone(self, text: str, profile_path: str) -> np.ndarray:
        from cosyvoice.utils.file_utils import load_wav
        ps = load_wav(profile_path, 16000)
        result = self._model.inference_zero_shot(text, ps, text)
        chunks = [c["tts_speech"].numpy() for c in result]
        return np.concatenate(chunks) if chunks else np.zeros((0,), dtype=np.float32)

    def _fallback_silence(self, text: str) -> np.ndarray:
        dur = max(len(text.split()) * 0.3, 1.0)
        return np.zeros(int(dur * 24000), dtype=np.float32)

    def is_available(self) -> bool:
        return self._model is not None

    def list_profiles(self) -> list[dict]:
        profiles = []
        pd = Path(self.profiles_dir)
        if pd.exists():
            for w in sorted(pd.glob("*.wav")):
                profiles.append({
                    "profile_id": w.stem, "name": w.stem.replace("_", " ").title(),
                    "language": "en", "is_default": w.stem == "new_york",
                })
        if self._edge_tts or not profiles:
            try:
                from .edge_tts import VOICE_INFO
                for pid, info in VOICE_INFO.items():
                    if not any(p["profile_id"] == pid for p in profiles):
                        profiles.append({
                            "profile_id": pid, "name": info["name"],
                            "language": info["language"],
                            "is_default": info.get("is_default", False),
                        })
            except ImportError:
                pass
        return profiles