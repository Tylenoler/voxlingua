# ============================================================
# VoxLingua AI Engine — Dockerfile
# 
# Build:   docker build -t voxlingua-engine -f engine/Dockerfile engine/
# Run:     docker run -p 9876:9876 voxlingua-engine
# ============================================================

FROM python:3.11-slim AS base

# ── System dependencies ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──
WORKDIR /app
COPY . .

# ── Model download (optional stage) ──
FROM base AS with-models
RUN python -c "
import whisper
whisper.load_model('large')
print('Whisper large model loaded')
"
# Note: CosyVoice model must be downloaded separately:
#   git lfs clone https://www.modelscope.cn/iic/CosyVoice-300M.git ./models/weights/cosyvoice/300m/

# ── Runtime ──
FROM base AS runtime
EXPOSE 9876

# Set default config
ENV LLM_API_KEY=""
ENV WHISPER_MODEL="large"

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9876/api/status')" || exit 1

CMD ["python", "server.py"]
