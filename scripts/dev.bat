@echo off
REM ============================================================
REM VoxLingua — Dev Launcher (Windows)
REM Starts both the AI engine and desktop app.
REM ============================================================

echo ========================================
echo   VoxLingua Dev Launcher
echo ========================================

REM ── Start engine in background ──
echo [1/2] Starting AI Engine...
start "VoxLingua Engine" cmd /c "cd engine && python server.py"
echo   Engine starting on port 9876...
echo.

REM ── Start desktop app ──
echo [2/2] Starting Desktop App...
cd desktop
start "VoxLingua Desktop" cmd /c "npm run dev"
echo   Desktop starting on http://localhost:5173...
echo.
echo   Press Ctrl+C in each window to stop.
echo ========================================
pause
