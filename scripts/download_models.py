#!/usr/bin/env python3
"""
VoxLingua — Model Download Script

Downloads all required ML models for offline use.

Usage:
    python scripts/download_models.py                  # Download all models
    python scripts/download_models.py --stt tiny        # Download specific variant
    python scripts/download_models.py --list            # List available models
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("download_models")


def download_whisper(variant: str = "large"):
    """Download Whisper model."""
    logger.info(f"Downloading Whisper '{variant}'...")
    import whisper
    model = whisper.load_model(variant)
    logger.info(f"  ✅ Whisper {variant} loaded (size: {sum(p.numel() for p in model.parameters()):,} params)")


def download_wav2vec2(variant: str = "large"):
    """Download Wav2Vec2 model for phoneme alignment."""
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    repo = {
        "base": "facebook/wav2vec2-base-960h",
        "large": "facebook/wav2vec2-large-960h-lv60-self",
    }[variant]

    logger.info(f"Downloading Wav2Vec2 '{variant}' from {repo}...")
    processor = Wav2Vec2Processor.from_pretrained(repo)
    model = Wav2Vec2ForCTC.from_pretrained(repo)
    logger.info(f"  ✅ Wav2Vec2 {variant} loaded")


def download_cosyvoice(variant: str = "300m"):
    """Download CosyVoice model.

    Note: CosyVoice must be downloaded from ModelScope or HuggingFace.
    This function provides instructions.
    """
    logger.info("CosyVoice model download instructions:")
    logger.info("")
    logger.info("  Option 1: ModelScope (recommended for Chinese users)")
    logger.info("    pip install modelscope")
    logger.info("    from modelscope.hub.snapshot_download import snapshot_download")
    logger.info('    snapshot_download("iic/CosyVoice-300M", local_dir="./models/weights/cosyvoice/300m")')
    logger.info("")
    logger.info("  Option 2: HuggingFace")
    logger.info("    git lfs install")
    logger.info("    git clone https://huggingface.co/FunAudioLLM/CosyVoice-300M ./models/weights/cosyvoice/300m")
    logger.info("")
    logger.info("  Option 3: Manual download")
    logger.info("    Visit: https://www.modelscope.cn/models/iic/CosyVoice-300M")
    logger.info("    Download and extract to: ./models/weights/cosyvoice/300m/")


def main():
    parser = argparse.ArgumentParser(description="Download VoxLingua ML models")
    parser.add_argument("--stt", nargs="?", const="large", help="Whisper variant (tiny/base/small/medium/large)")
    parser.add_argument("--aligner", nargs="?", const="large", help="Wav2Vec2 variant (base/large)")
    parser.add_argument("--tts", nargs="?", const="300m", help="CosyVoice variant (300m)")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--all", action="store_true", help="Download all models")

    args = parser.parse_args()

    model_dir = Path(__file__).parent.parent / "engine" / "models" / "weights"
    model_dir.mkdir(parents=True, exist_ok=True)

    if args.list:
        print("Available models:")
        print("  --stt     tiny/base/small/medium/large (default: large)")
        print("  --aligner base/large (default: large)")
        print("  --tts     300m (instructions only)")
        return

    if args.stt or args.all:
        download_whisper(args.stt or "large")

    if args.aligner or args.all:
        download_wav2vec2(args.aligner or "large")

    if args.tts or args.all:
        download_cosyvoice(args.tts or "300m")

    if not any([args.stt, args.aligner, args.tts, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
