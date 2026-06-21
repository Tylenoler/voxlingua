#!/usr/bin/env bash
# ============================================================
# VoxLingua — Dev Launcher (macOS / Linux)
# Starts both the AI engine and desktop app.
# ============================================================

set -e

echo "========================================"
echo "  VoxLingua Dev Launcher"
echo "========================================"
echo ""

# ── Start engine in background ──
echo "[1/2] Starting AI Engine..."
cd "$(dirname "$0")/.."
cd engine
python3 server.py &
ENGINE_PID=$!
echo "  Engine starting on port 9876 (PID: $ENGINE_PID)"
cd ..
echo ""

# ── Start desktop app ──
echo "[2/2] Starting Desktop App..."
cd desktop
npm run dev &
DESKTOP_PID=$!
echo "  Desktop starting on http://localhost:5173 (PID: $DESKTOP_PID)"
cd ..
echo ""

echo "========================================"
echo "  Press Ctrl+C to stop both processes"
echo "========================================"

# Cleanup on exit
trap "kill $ENGINE_PID $DESKTOP_PID 2>/dev/null; exit" INT TERM
wait
