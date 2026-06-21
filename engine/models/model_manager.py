"""
VoxLingua — Model Manager

Handles downloading, caching, and lifecycle of ML models:
  - Whisper (STT)
  - Wav2Vec2 (phoneme alignment)
  - CosyVoice 3 (TTS + voice cloning)

Models are stored under engine/models/weights/{model_name}/
"""

import hashlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("voxlingua.models")

MODELS_DIR = Path(__file__).parent / "weights"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Model Registry ──

MODEL_REGISTRY = {
    "whisper": {
        "variants": {
            "tiny": {"repo": "openai/whisper-tiny", "size_mb": 150},
            "base": {"repo": "openai/whisper-base", "size_mb": 290},
            "small": {"repo": "openai/whisper-small", "size_mb": 970},
            "medium": {"repo": "openai/whisper-medium", "size_mb": 3100},
            "large": {"repo": "openai/whisper-large-v3", "size_mb": 6450},
        },
        "default": "large",
        "description": "OpenAI Whisper for speech-to-text with word-level timestamps",
    },
    "wav2vec2": {
        "variants": {
            "base": {"repo": "facebook/wav2vec2-base-960h", "size_mb": 1400},
            "large": {"repo": "facebook/wav2vec2-large-960h-lv60-self", "size_mb": 4700},
        },
        "default": "large",
        "description": "Wav2Vec2 for CTC forced alignment and phoneme recognition",
    },
    "cosyvoice": {
        "variants": {
            "300m": {"repo": "FunAudioLLM/CosyVoice-300M", "size_mb": 3900},
            "300m_sft": {"repo": "FunAudioLLM/CosyVoice-300M-SFT", "size_mb": 3600},
            "300m_instruct": {"repo": "FunAudioLLM/CosyVoice-300M-Instruct", "size_mb": 3600},
        },
        "default": "300m",
        "description": "CosyVoice 3 for TTS with voice cloning and streaming",
    },
}


def get_model_path(model_type: str, variant: str = "") -> Path:
    """Get the local path for a model, downloading if needed."""
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(MODEL_REGISTRY.keys())}")

    registry = MODEL_REGISTRY[model_type]
    if not variant:
        variant = registry["default"]

    if variant not in registry["variants"]:
        raise ValueError(f"Unknown variant '{variant}' for {model_type}. Available: {list(registry['variants'].keys())}")

    model_dir = MODELS_DIR / model_type / variant
    marker_file = model_dir / ".downloaded"

    if marker_file.exists():
        logger.info(f"Model {model_type}/{variant} found locally at {model_dir}")
        return model_dir

    logger.warning(f"Model {model_type}/{variant} not downloaded yet at {model_dir}")
    return model_dir


def is_model_downloaded(model_type: str, variant: str = "") -> bool:
    """Check if a model is already downloaded."""
    try:
        path = get_model_path(model_type, variant)
        return (path / ".downloaded").exists()
    except (ValueError, KeyError):
        return False


def mark_model_downloaded(model_type: str, variant: str):
    """Mark a model as successfully downloaded."""
    model_dir = MODELS_DIR / model_type / variant
    model_dir.mkdir(parents=True, exist_ok=True)
    marker = model_dir / ".downloaded"
    marker.touch()
    logger.info(f"Model {model_type}/{variant} marked as downloaded")


def get_download_instructions(model_type: str) -> str:
    """Get human-readable download instructions for a model."""
    registry = MODEL_REGISTRY.get(model_type)
    if not registry:
        return f"Unknown model type: {model_type}"

    lines = [f"=== {model_type.upper()} Download Instructions ==="]
    for variant, info in registry["variants"].items():
        is_def = " (default)" if variant == registry["default"] else ""
        lines.append(f"  [{variant}]{is_def} ~{info['size_mb']}MB from {info['repo']}")

    if model_type == "whisper":
        lines.append("\n  Use: whisper.load_model('{variant}')")
    elif model_type == "wav2vec2":
        lines.append("\n  Use: Wav2Vec2ForCTC.from_pretrained('{repo}')")
    elif model_type == "cosyvoice":
        lines.append("\n  Use: CosyVoice('{local_path}')")
        lines.append("\n  Download from: https://www.modelscope.cn/models/iic/CosyVoice-300M")
        lines.append("  Or using git lfs:")
        lines.append("    git lfs install")
        lines.append("    git clone https://www.modelscope.cn/iic/CosyVoice-300M.git")

    return "\n".join(lines)


# ── Model lifecycle ──

_model_instances: dict[str, object] = {}


def warmup_models(config: dict) -> dict[str, bool]:
    """Pre-load models on server startup based on config.

    Returns dict of model_name -> loaded_successfully
    """
    results = {}

    # STT model
    stt_cfg = config.get("models", {}).get("stt", {})
    stt_variant = stt_cfg.get("model", "large")
    try:
        from stt.whisper_stt import WhisperSTT
        _model_instances["stt"] = WhisperSTT(model_size=stt_variant)
        results["stt"] = True
        logger.info(f"STT model (whisper/{stt_variant}) loaded")
    except Exception as e:
        results["stt"] = False
        logger.warning(f"STT model load failed (will lazy-load): {e}")

    # TTS model
    tts_cfg = config.get("models", {}).get("tts", {})
    tts_dir = tts_cfg.get("model_dir", str(MODELS_DIR / "cosyvoice" / "300m"))
    try:
        from tts.cosyvoice_tts import CosyVoiceTTS
        _model_instances["tts"] = CosyVoiceTTS(model_dir=tts_dir)
        results["tts"] = True
        logger.info(f"TTS model (CosyVoice) loaded from {tts_dir}")
    except Exception as e:
        results["tts"] = False
        logger.warning(f"TTS model load failed (will lazy-load): {e}")

    return results


def get_model(name: str):
    """Get a loaded model instance, raising if not loaded."""
    instance = _model_instances.get(name)
    if instance is None:
        raise RuntimeError(f"Model '{name}' not loaded. Call warmup_models() first or check config.")
    return instance


def set_model(name: str, instance: object):
    """Register a model instance (for lazy loading)."""
    _model_instances[name] = instance
