@echo off
REM ============================================================
REM VoxLingua — CosyVoice 3 Setup Script
REM
REM Installs CosyVoice 3 from FunAudioLLM and its dependencies.
REM Requires Microsoft Visual C++ Build Tools for matcha-tts.
REM ============================================================

echo ========================================
echo  VoxLingua CosyVoice 3 Setup
echo ========================================
echo.

REM Step 1: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10-3.12.
    exit /b 1
)

REM Step 2: Install system dependencies
echo [1/5] Installing C++ build tools (required for matcha-tts)...
echo   Download VS Build Tools...
curl -L -o "%TEMP%\vs_BuildTools.exe" https://aka.ms/vs/17/release/vs_BuildTools.exe >nul 2>&1
echo   Installing... (this may take several minutes)
start /wait "" "%TEMP%\vs_BuildTools.exe" --quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --includeRecommended 2>&1
echo   Done.

REM Step 3: Install matcha-tts
echo [2/5] Installing matcha-tts...
pip install matcha-tts
if %errorlevel% neq 0 (
    echo [WARNING] matcha-tts installation failed. TTS will use edge-tts fallback.
)

REM Step 4: Clone and install CosyVoice
echo [3/5] Cloning CosyVoice repo...
if not exist "%TEMP%\cosyvoice" (
    git clone --depth=1 https://github.com/FunAudioLLM/CosyVoice.git "%TEMP%\cosyvoice"
)
echo   Installing dependencies...
pip install torchaudio hyperpyyaml conformer
if exist "%TEMP%\cosyvoice\cosyvoice" (
    cd "%TEMP%\cosyvoice"
    pip install -r requirements.txt --no-deps 2>nul
)
cd /d "%~dp0.."

REM Step 5: Download CosyVoice-300M model
echo [4/5] Downloading CosyVoice-300M model (3.9GB, may take a while)...
python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice-300M', cache_dir=r'engine\models\weights\cosyvoice')"
if %errorlevel% equ 0 (
    echo   Model downloaded successfully!
) else (
    echo   Download manually: python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice-300M')"
)

REM Step 6: Verify
echo [5/5] Verifying installation...
python -c "
import sys
sys.path.insert(0, r'%TEMP%\cosyvoice')
from cosyvoice.cli.cosyvoice import CosyVoice
model = CosyVoice(r'engine\models\weights\cosyvoice\iic\CosyVoice-300M')
print('CosyVoice 3 loaded successfully!')
"

echo ========================================
echo  CosyVoice 3 setup complete!
echo  If matcha-tts installation failed, edge-tts
echo  will be used as TTS fallback.
echo ========================================
pause