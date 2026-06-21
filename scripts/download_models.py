#!/usr/bin/env python3
"""Download VoxLingua ML models."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("download_models")


def download_whisper(variant: str = "large"):
    """Download Whisper model."""
    import whisper
    logger.info(f"Downloading Whisper '{variant}'...")
    model = whisper.load_model(variant)
    size = sum(p.numel() for p in model.parameters())
    logger.info(f"  OK: Whisper {variant} loaded ({size:,} params)")


def download_wav2vec2(variant: str = "base"):
    """Download Wav2Vec2 model from HuggingFace."""
    from models.model_manager import MODELS_DIR, mark_model_downloaded
    from huggingface_hub import snapshot_download

    repo = {
        "base": "facebook/wav2vec2-base-960h",
        "large": "facebook/wav2vec2-large-960h-lv60-self",
    }[variant]

    model_dir = MODELS_DIR / "wav2vec2" / variant
    model_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading Wav2Vec2 '{variant}' from {repo}...")
    logger.info(f"  Target: {model_dir}")
    snapshot_download(repo, local_dir=str(model_dir), local_dir_use_symlinks=False)
    mark_model_downloaded("wav2vec2", variant)
    logger.info(f"  OK: Wav2Vec2 {variant} downloaded")


def download_cosyvoice():
    """Download CosyVoice-300M model from ModelScope."""
    logger.info("Downloading CosyVoice-300M from ModelScope...")
    logger.info("  This requires modelscope package.")
    logger.info("  pip install modelscope")
    try:
        from modelscope import snapshot_download
        from models.model_manager import MODELS_DIR
        model_dir = MODELS_DIR / "cosyvoice" / "iic" / "CosyVoice-300M"
        model_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download("iic/CosyVoice-300M", cache_dir=str(MODELS_DIR / "cosyvoice"))
        from models.model_manager import mark_model_downloaded
        mark_model_downloaded("cosyvoice", "iic/CosyVoice-300M")
        logger.info(f"  OK: CosyVoice-300M downloaded to {model_dir}")
    except ImportError:
        logger.info("  modelscope not installed. Run: pip install modelscope")
    except Exception as e:
        logger.warning(f"  Download failed: {e}")
def main():
    parser = argparse.ArgumentParser(description="Download VoxLingua ML models")
    parser.add_argument("--stt", nargs="?", const="large", help="Whisper variant")
    parser.add_argument("--aligner", nargs="?", const="base", help="Wav2Vec2 variant (base/large)")
    parser.add_argument("--tts", action="store_true", help="Show CosyVoice instructions")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--all", action="store_true", help="Download all available models")

    args = parser.parse_args()

    if args.list:
        print("Available models:")
        print("  --stt     tiny/base/small/medium/large (default: large)")
        print("  --aligner base/large (default: base)")
        print("  --tts     Download CosyVoice-300M model")
        return

    if args.all:
        download_whisper("large")
        download_wav2vec2("base")
        download_cosyvoice()
        return

    if args.stt:
        download_whisper(args.stt)
    if args.aligner:
        download_wav2vec2(args.aligner)
    if args.tts:
        download_cosyvoice()

    if not any([args.stt, args.aligner, args.tts, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()