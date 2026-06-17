# VoxLingua Development Setup — Windows PowerShell
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1
#         powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -SkipModels
#
# This script will:
#   1. Check prerequisites (Python 3.11+, Node 18+, Rust 1.75+ [optional])
#   2. Create Python virtual environment
#   3. Install Python dependencies (STT, TTS, LLM, correction)
#   4. Install Node.js dependencies (desktop UI)
#   5. Download AI model weights (CosyVoice 3, Whisper, Wav2Vec2)
#   6. Print post-setup instructions

param(
    [switch]$SkipModels = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$EngineDir = Join-Path $ProjectRoot "engine"
$DesktopDir = Join-Path $ProjectRoot "desktop"
$ScriptsDir = Join-Path $ProjectRoot "scripts"

function Write-Info  { Write-Host "[INFO] $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

# ── 1. Check prerequisites ──────────────────────────────────────

Write-Info "Checking prerequisites..."

$PythonOK = $false
try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -ge 3 -and $minor -ge 11) {
            $PythonOK = $true
            Write-Info "Python $($matches[0]) — OK"
        } else {
            Write-Warn "Python 3.11+ required (found $($matches[0]))"
        }
    }
} catch {
    Write-Error "Python not found. Install Python 3.11+ from https://python.org"
    exit 1
}

$NodeOK = $false
try {
    $nodeVer = node --version 2>&1
    if ($nodeVer) {
        Write-Info "Node $nodeVer — OK"
        $NodeOK = $true
    }
} catch {
    Write-Warn "Node.js not found. Desktop UI setup will be skipped."
}

$RustOK = $false
try {
    $rustVer = rustc --version 2>&1
    if ($rustVer -match "(\d+\.\d+\.\d+)") {
        Write-Info "Rust $($matches[1]) — OK"
        $RustOK = $true
    }
} catch {
    Write-Warn "Rust not found. Tauri packaging will be unavailable."
}

# ── 2. Python virtual environment ────────────────────────────────

Write-Info "Setting up Python virtual environment..."
$venvPath = Join-Path $EngineDir ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Info "Virtual environment created at engine\.venv"
}

# Activate venv
& "$venvPath\Scripts\Activate.ps1"

# ── 3. Install Python dependencies ───────────────────────────────

Write-Info "Installing Python dependencies..."
Set-Location $EngineDir
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
Write-Info "Python dependencies installed"

# ── 4. Install desktop UI dependencies ───────────────────────────

if ($NodeOK) {
    Write-Info "Installing desktop UI dependencies..."
    Set-Location $DesktopDir
    npm install --silent 2>$null
    Write-Info "Desktop UI dependencies installed"
}

# ── 5. Download AI models ────────────────────────────────────────

if (-not $SkipModels) {
    Write-Info "Downloading AI model weights (this may take a while)..."

    # CosyVoice 3 TTS model
    $cvModelYaml = Join-Path $EngineDir "models\cosyvoice\model.yaml"
    if (-not (Test-Path $cvModelYaml)) {
        Write-Info "Downloading CosyVoice 3 TTS model..."
        python (Join-Path $ScriptsDir "download_tts_model.py") --model v3
    } else {
        Write-Info "CosyVoice model already downloaded — skipping"
    }

    Write-Info "Whisper and Wav2Vec2 models will be downloaded on first use"
    Write-Info "  Whisper cache: ~\.cache\whisper\"
    Write-Info "  Torch cache:   ~\.cache\torch\"
} else {
    Write-Info "Skipping model downloads (-SkipModels)"
}

# Ensure engine/models directory exists
$null = New-Item -ItemType Directory -Force -Path (Join-Path $EngineDir "models")

# ── 6. Print summary ─────────────────────────────────────────────

Set-Location $ProjectRoot

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VoxLingua — Setup Complete" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Start the engine:"
Write-Host "    cd engine"
Write-Host "    .venv\Scripts\Activate.ps1"
Write-Host "    python server.py"
Write-Host ""
Write-Host "  Start the desktop UI (separate terminal):"
Write-Host "    cd desktop"
Write-Host "    npm run dev"
Write-Host ""
if ($RustOK) {
    Write-Host "  Package as desktop app:"
    Write-Host "    cd desktop"
    Write-Host "    npm run tauri build"
    Write-Host ""
}
Write-Host "  Check engine status:"
Write-Host "    curl http://localhost:9876/api/status"
Write-Host ""
Write-Host "  Run tests:"
Write-Host "    cd engine"
Write-Host "    python -m pytest tests/ -v"
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
