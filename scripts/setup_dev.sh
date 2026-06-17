#!/usr/bin/env bash
#
# VoxLingua Development Setup — Unix/macOS
#
# Usage:  bash scripts/setup_dev.sh
#         bash scripts/setup_dev.sh --skip-models   # skip model downloads
#
# This script will:
#   1. Check prerequisites (Python 3.11+, Node 18+, Rust 1.75+ [optional])
#   2. Create Python virtual environment
#   3. Install Python dependencies (STT, TTS, LLM, correction)
#   4. Install Node.js dependencies (desktop UI)
#   5. Download AI model weights (Whisper, CosyVoice 3, Wav2Vec2)
#   6. Print post-setup instructions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

SKIP_MODELS=false
for arg in "$@"; do
    case "$arg" in
        --skip-models) SKIP_MODELS=true ;;
    esac
done

# ── 1. Check prerequisites ──────────────────────────────────────

info "Checking prerequisites..."

PYTHON_OK=false
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
        PYTHON_OK=true
        info "Python $PY_VER — OK"
    else
        warn "Python 3.11+ required (found $PY_VER)"
    fi
else
    error "python3 not found. Install Python 3.11+ from https://python.org"
    exit 1
fi

NODE_OK=false
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    info "Node $NODE_VER — OK"
    NODE_OK=true
else
    warn "Node.js not found. Desktop UI setup will be skipped."
    warn "Install from https://nodejs.org"
fi

RUST_OK=false
if command -v rustc &>/dev/null; then
    RUST_VER=$(rustc --version | awk '{print $2}')
    info "Rust $RUST_VER — OK"
    RUST_OK=true
else
    warn "Rust not found. Tauri desktop packaging will be unavailable."
    warn "Install from https://rustup.rs"
fi

# ── 2. Python virtual environment ────────────────────────────────

info "Setting up Python virtual environment..."
if [ ! -d "$PROJECT_ROOT/engine/.venv" ]; then
    python3 -m venv "$PROJECT_ROOT/engine/.venv"
    info "Virtual environment created at engine/.venv"
fi

source "$PROJECT_ROOT/engine/.venv/bin/activate"

# ── 3. Install Python dependencies ───────────────────────────────

info "Installing Python dependencies..."
cd "$PROJECT_ROOT/engine"
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "Python dependencies installed"

# ── 4. Install desktop UI dependencies ───────────────────────────

if [ "$NODE_OK" = true ]; then
    info "Installing desktop UI dependencies..."
    cd "$PROJECT_ROOT/desktop"
    npm install --silent 2>/dev/null
    info "Desktop UI dependencies installed"
fi

# ── 5. Download AI models ────────────────────────────────────────

if [ "$SKIP_MODELS" = false ]; then
    info "Downloading AI model weights (this may take a while)..."

    # CosyVoice 3 TTS model (~2 GB)
    if [ ! -f "$PROJECT_ROOT/engine/models/cosyvoice/model.yaml" ]; then
        info "Downloading CosyVoice 3 TTS model..."
        python "$PROJECT_ROOT/scripts/download_tts_model.py" --model v3
    else
        info "CosyVoice model already downloaded — skipping"
    fi

    # Whisper + Wav2Vec2 models are downloaded on first use by their respective
    # libraries and cached automatically in ~/.cache/
    info "Whisper and Wav2Vec2 models will be downloaded on first use"
    info "  Whisper cache: ~/.cache/whisper/"
    info "  Torchaudio cache: ~/.cache/torch/"
else
    info "Skipping model downloads (--skip-models)"
fi

# Ensure engine/models directory exists for TTS
mkdir -p "$PROJECT_ROOT/engine/models"

# ── 6. Print summary ─────────────────────────────────────────────

cd "$PROJECT_ROOT"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}VoxLingua — Setup Complete${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Start the engine:"
echo "    cd engine && source .venv/bin/activate && python server.py"
echo ""
echo "  Start the desktop UI (separate terminal):"
echo "    cd desktop && npm run dev"
echo ""
if [ "$RUST_OK" = true ]; then
    echo "  Package as desktop app:"
    echo "    cd desktop && npm run tauri build"
    echo ""
fi
echo "  Check engine status:"
echo "    curl http://localhost:9876/api/status"
echo ""
echo "  Run tests:"
echo "    cd engine && python -m pytest tests/ -v"
echo ""
echo "═══════════════════════════════════════════════════════════"
