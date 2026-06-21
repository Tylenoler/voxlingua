#!/usr/bin/env bash
# ============================================================
# VoxLingua — Unix Setup Script (macOS / Linux)
# ============================================================

set -e

echo "========================================"
echo "  VoxLingua Setup"
echo "========================================"
echo ""

# ── Check prerequisites ──
echo "[1/4] Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3.11+ required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js 18+ required"; exit 1; }
echo "  Python OK & Node OK"
echo ""

# ── Install Python dependencies ──
echo "[2/4] Installing Python engine dependencies..."
cd engine
python3 -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Engine dependencies installed"
cd ..
echo ""

# ── Install desktop dependencies ──
echo "[3/4] Installing desktop app dependencies..."
cd desktop
npm install --silent
echo "  Desktop dependencies installed"
cd ..
echo ""

# ── Create voice profiles directory ──
echo "[4/4] Creating voice profiles directory..."
mkdir -p engine/voice_profiles
echo "  Place your reference .wav files in engine/voice_profiles/"
echo "  e.g., new_york.wav for the NYC accent profile"
echo ""

echo "========================================"
echo "  Setup complete!"
echo ""
echo "  To start the engine:"
echo "    cd engine && python3 server.py"
echo ""
echo "  To start the desktop app (new terminal):"
echo "    cd desktop && npm run dev"
echo ""
echo "  Then open http://localhost:5173"
echo "========================================"
