@echo off
REM ============================================================
REM VoxLingua — Windows Setup Script
REM ============================================================

echo ========================================
echo   VoxLingua Setup
echo ========================================
echo.

REM ── Check prerequisites ──
echo [1/4] Checking prerequisites...
python --version >nul 2>&1 || (
    echo ERROR: Python 3.11+ is required. Download from https://python.org
    pause
    exit /b 1
)
node --version >nul 2>&1 || (
    echo ERROR: Node.js 18+ is required. Download from https://nodejs.org
    pause
    exit /b 1
)
echo   Python OK ^& Node OK
echo.

REM ── Install Python dependencies ──
echo [2/4] Installing Python engine dependencies...
cd engine
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo   Engine dependencies installed
cd ..
echo.

REM ── Install desktop dependencies ──
echo [3/4] Installing desktop app dependencies...
cd desktop
call npm install
echo   Desktop dependencies installed
cd ..
echo.

REM ── Create voice profiles directory ──
echo [4/4] Creating voice profiles directory...
if not exist engine\voice_profiles (
    mkdir engine\voice_profiles
    echo   Place your reference .wav files in engine/voice_profiles/
    echo   e.g., new_york.wav for the NYC accent profile
)
echo.

echo ========================================
echo   Setup complete!
echo.
echo   To start the engine:
echo     cd engine ^&^& python server.py
echo.
echo   To start the desktop app (another terminal):
echo     cd desktop ^&^& npm run dev
echo.
echo   Then open http://localhost:5173 in your browser
echo ========================================
pause
