#!/usr/bin/env python3
"""
Download CosyVoice 3 TTS model weights from Hugging Face.

Usage
-----
    python scripts/download_tts_model.py                    # CosyVoice 3 (default)
    python scripts/download_tts_model.py --model v2         # CosyVoice 2 fallback
    python scripts/download_tts_model.py --dir ./my_models  # custom output dir

The model is saved to ``engine/models/cosyvoice/`` (or the directory
specified by ``--dir``).  The engine's ``config.yaml`` references this path.

Requirements
------------
    pip install huggingface_hub
"""

import argparse
import logging
import os
import sys

# Add project root to path so we can import config if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("download_tts")

# Known CosyVoice model repositories on Hugging Face
MODEL_REPOS = {
    "v3": "FunAudioLLM/Fun-CosyVoice3-0.5B-2512",
    "v2": "FunAudioLLM/CosyVoice2-0.5B",
    "v1": "FunAudioLLM/CosyVoice-300M",
}

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "engine", "models", "cosyvoice"
)


def download_model(
    repo_id: str,
    output_dir: str,
    token: str | None = None,
    resume: bool = True,
) -> bool:
    """Download a Hugging Face repo snapshot to *output_dir*.

    Returns ``True`` on success.
    """
    from huggingface_hub import snapshot_download

    os.makedirs(output_dir, exist_ok=True)

    logger.info("Downloading model: %s", repo_id)
    logger.info("Output directory: %s", output_dir)
    logger.info("This may take several minutes (model is ~2 GB)…")

    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=output_dir,
            local_dir_use_symlinks=False,
            resume_download=resume,
            token=token,
            ignore_patterns=["*.pt", "*.bin"],  # skip redundant checkpoints
        )
        logger.info("Download complete!")
        return True

    except Exception as exc:
        logger.error("Download failed: %s", exc)
        return False


def verify_model(output_dir: str) -> bool:
    """Check that the downloaded directory looks like a valid CosyVoice model."""
    required_files = ["model.yaml"]
    missing = [f for f in required_files if not os.path.isfile(os.path.join(output_dir, f))]

    if missing:
        logger.warning("Model directory missing required files: %s", missing)
        return False

    # Check for model weights (onnx or torch)
    has_weights = any(
        os.path.isfile(os.path.join(output_dir, f))
        for f in os.listdir(output_dir)
        if f.endswith((".onnx", ".pt", ".pth", ".safetensors", ".bin"))
    ) or any(
        os.path.isdir(os.path.join(output_dir, d))
        and any(
            f.endswith((".onnx", ".pt", ".pth", ".safetensors", ".bin"))
            for f in os.listdir(os.path.join(output_dir, d))
        )
        for d in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, d))
    )

    if not has_weights:
        logger.warning(
            "No model weight files found in %s. "
            "The model may not be usable yet.",
            output_dir,
        )
        return False

    return True


def list_available_models() -> list[str]:
    """List models available for download."""
    return list(MODEL_REPOS.keys())


def main():
    parser = argparse.ArgumentParser(
        description="Download CosyVoice TTS model weights from Hugging Face"
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_REPOS.keys()),
        default="v3",
        help="Which CosyVoice model version to download (default: v3)",
    )
    parser.add_argument(
        "--dir",
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Hugging Face token (required for gated models)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Do not resume a previous partial download",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available model versions and exit",
    )
    parser.add_argument(
        "--verify-only",
        metavar="DIR",
        nargs="?",
        const=DEFAULT_OUTPUT,
        help="Verify an already-downloaded model directory without downloading",
    )

    args = parser.parse_args()

    if args.list_models:
        print("Available CosyVoice models:")
        for key, repo in MODEL_REPOS.items():
            print(f"  {key:4s} → {repo}")
        return

    if args.verify_only:
        valid = verify_model(args.verify_only)
        if valid:
            logger.info("Model at '%s' looks valid ✓", args.verify_only)
        else:
            logger.error("Model at '%s' is incomplete or invalid", args.verify_only)
            sys.exit(1)
        return

    repo_id = MODEL_REPOS[args.model]
    output_dir = os.path.abspath(args.dir)

    logger.info("=" * 60)
    logger.info("CosyVoice TTS Model Downloader")
    logger.info("=" * 60)
    logger.info("Model:   %s (%s)", args.model, repo_id)
    logger.info("Output:  %s", output_dir)
    logger.info("")

    # Check if already downloaded
    if os.path.isdir(output_dir) and verify_model(output_dir):
        logger.info("Model already exists and is valid at '%s'", output_dir)
        logger.info("Use --verify-only to re-check, or delete the directory to re-download.")
        return

    success = download_model(
        repo_id=repo_id,
        output_dir=output_dir,
        token=args.token,
        resume=args.resume,
    )

    if success and verify_model(output_dir):
        logger.info("✅ CosyVoice model '%s' ready at:", args.model)
        logger.info("   %s", output_dir)
        logger.info("")
        logger.info("Next steps:")
        logger.info("   1. Install cosyvoice:  pip install cosyvoice")
        logger.info("   2. Start the engine:   cd engine && python server.py")
        logger.info("   3. Check status:       curl http://localhost:9876/api/status")
    else:
        logger.error("❌ Model download failed or model is incomplete.")
        logger.error("   Try: python scripts/download_tts_model.py --model v2")
        sys.exit(1)


if __name__ == "__main__":
    main()
