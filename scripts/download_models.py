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


def show_cosyvoice_instructions():
    logger.info("CosyVoice download instructions:")
    logger.info("")
    logger.info("  Option 1: ModelScope")
    logger.info("    pip install modelscope")
    logger.info('    python -c "from modelscope.hub.snapshot_download import snapshot_download;')
    logger.info('        snapshot_download(\"iic/CosyVoice-300M\",')
    logger.info('            local_dir=\"./models/weights/cosyvoice/300m\")"')
    logger.info("")
    logger.info("  Option 2: HuggingFace")
    logger.info("    git lfs install")
    logger.info("    git clone https://huggingface.co/FunAudioLLM/CosyVoice-300M ./models/weights/cosyvoice/300m")


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
        print("  --tts     Show CosyVoice download instructions")
        return

    if args.all:
        download_whisper("large")
        download_wav2vec2("base")
        show_cosyvoice_instructions()
        return

    if args.stt:
        download_whisper(args.stt)
    if args.aligner:
        download_wav2vec2(args.aligner)
    if args.tts:
        show_cosyvoice_instructions()

    if not any([args.stt, args.aligner, args.tts, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()