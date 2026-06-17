#!/usr/bin/env python3
"""
VoxLingua AI Engine — FastAPI Server

Provides:
  - REST API for STT, LLM Chat, TTS, Scoring, Correction
  - WebSocket server for mobile app streaming
  - mDNS discovery broadcast
"""

import os
import sys
import json
import logging

import yaml
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Add engine directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import stt, chat, tts, scorer, correction
from core.session_manager import session_manager
from core.pipeline import ConversationPipeline
from core.stt_engine import WhisperSTTEngine, set_stt_engine, get_stt_engine
from core.tts_engine import CosyVoiceEngine, set_tts_engine, get_tts_engine
from core.phoneme_aligner import Wav2Vec2Aligner, set_aligner, get_aligner
from llm.cloud import CloudLLMClient, get_llm_client, set_llm_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voxlingua.engine")

app = FastAPI(
    title="VoxLingua AI Engine",
    version="1.0.0",
    description="AI-powered spoken language practice with voice cloning & correction",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST routers
app.include_router(stt.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(scorer.router)
app.include_router(correction.router)

# Global pipeline
pipeline = ConversationPipeline()

# Active WebSocket connections
_ws_connections: dict[str, WebSocket] = {}

# App-level config (loaded at startup)
_app_config: dict = {}


# ── REST Endpoints ──


@app.get("/api/status")
async def get_status():
    """Get engine status."""
    llm_available = False
    try:
        llm_available = get_llm_client().is_available()
    except Exception:
        pass

    stt_loaded = False
    try:
        stt_engine = get_stt_engine()
        stt_loaded = stt_engine.is_loaded()
    except Exception:
        pass

    tts_loaded = False
    try:
        tts_engine = get_tts_engine()
        tts_loaded = tts_engine.is_loaded()
    except Exception:
        pass

    aligner_loaded = False
    try:
        aligner = get_aligner()
        aligner_loaded = aligner.is_loaded()
    except Exception:
        pass

    return {
        "status": "running",
        "version": "1.0.0",
        "llm_connected": llm_available,
        "stt_loaded": stt_loaded,
        "tts_loaded": tts_loaded,
        "aligner_loaded": aligner_loaded,
        "active_sessions": session_manager.active_count,
        "connected_devices": len(_ws_connections),
    }


@app.get("/api/voices")
async def list_voices():
    """List available voice profiles from the TTS engine."""
    try:
        engine = get_tts_engine()
        voices = engine.list_voices()
        if not voices:
            voices = [
                {
                    "profile_id": "new_york",
                    "name": "New York Accent (default)",
                    "language": "en",
                    "is_default": True,
                }
            ]
    except Exception:
        voices = [
            {
                "profile_id": "new_york",
                "name": "New York Accent (default)",
                "language": "en",
                "is_default": True,
            }
        ]

    return {"voices": voices}


@app.get("/api/scenes")
async def list_scenes():
    """List available conversation scenes."""
    return {
        "scenes": [
            {"id": "daily_chat", "name": "Daily Chat", "description": "Casual everyday conversation"},
            {"id": "restaurant", "name": "Restaurant", "description": "Ordering food and drinks"},
            {"id": "travel", "name": "Travel", "description": "Airport, hotel, directions"},
            {"id": "interview", "name": "Job Interview", "description": "Professional interview practice"},
        ]
    }


# ── WebSocket ──


@app.websocket("/ws/mobile")
async def mobile_websocket(ws: WebSocket):
    """WebSocket endpoint for mobile app."""
    await ws.accept()
    session_id = f"sess_{os.urandom(6).hex()}"
    _ws_connections[session_id] = ws
    logger.info(f"Mobile connected: {session_id}")

    try:
        # Send handshake acknowledgment
        await ws.send_json({
            "type": "handshake_ack",
            "payload": {
                "session_id": session_id,
                "server_version": "1.0.0",
                "supported_languages": ["en"],
                "status": "ready",
            },
        })

        # Create session
        session = session_manager.create_session(session_id=session_id)

        # Message loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "payload": {"message": "Invalid JSON"}})
                continue

            msg_type = msg.get("type")
            payload = msg.get("payload", {})

            if msg_type == "handshake":
                await ws.send_json({
                    "type": "handshake_ack",
                    "payload": {
                        "session_id": session_id,
                        "server_version": "1.0.0",
                        "supported_languages": ["en"],
                        "status": "ready",
                    },
                })

            elif msg_type == "audio_input":
                # Process audio through pipeline
                result = pipeline.process_audio(
                    session_id=session_id,
                    audio_b64=payload.get("data", ""),
                    audio_format=payload.get("format", "opus"),
                    sample_rate=payload.get("sample_rate", 16000),
                )

                if "error" in result:
                    await ws.send_json({"type": "error", "payload": {"message": result["error"]}})
                    continue

                # Send streaming audio chunks
                for stream_msg in result["stream"]:
                    await ws.send_json(stream_msg)

                # Send correction
                if result.get("correction"):
                    await ws.send_json({
                        "type": "correction",
                        "payload": result["correction"],
                    })

            elif msg_type == "set_scene":
                session.scene = payload.get("scene", session.scene)
                session.language = payload.get("language", session.language)
                await ws.send_json({
                    "type": "scene_updated",
                    "payload": {
                        "scene": session.scene,
                        "language": session.language,
                    },
                })

            elif msg_type == "set_voice":
                session.voice_profile = payload.get("voice_profile_id", session.voice_profile)
                await ws.send_json({
                    "type": "voice_updated",
                    "payload": {"voice_profile": session.voice_profile},
                })

            elif msg_type == "set_correction_mode":
                from models.schemas import CorrectionMode
                session.correction_mode = CorrectionMode(
                    mode=payload.get("mode", "medium"),
                    interrupt_on_severe=payload.get("interrupt_on_severe", True),
                )
                await ws.send_json({
                    "type": "correction_mode_updated",
                    "payload": session.correction_mode.model_dump(),
                })

            else:
                await ws.send_json({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"},
                })

    except WebSocketDisconnect:
        logger.info(f"Mobile disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _ws_connections.pop(session_id, None)
        session_manager.remove_session(session_id)


# ── Startup / Shutdown ──


@app.on_event("startup")
async def startup():
    """Initialize engine on startup."""
    logger.info("=" * 50)
    logger.info("  VoxLingua AI Engine starting...")
    logger.info("=" * 50)

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            _app_config.update(yaml.safe_load(f) or {})
        logger.info(f"Config loaded from {config_path}")

        # Initialize LLM client
        _init_llm()

        # Initialize STT engine (Whisper)
        _init_stt()

        # Initialize TTS engine (CosyVoice)
        _init_tts()

        # Initialize phoneme aligner (Wav2Vec2 + CMUdict)
        _init_aligner()
    else:
        logger.warning("config.yaml not found, using defaults")

    logger.info("Engine ready. Listening on port 9876...")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down VoxLingua engine...")
    try:
        stt = get_stt_engine()
        stt.unload()
    except Exception:
        pass
    try:
        tts = get_tts_engine()
        tts.unload()
    except Exception:
        pass
    try:
        aligner = get_aligner()
        aligner.unload()
    except Exception:
        pass


def _init_llm():
    """Configure and initialise the LLM client from app config."""
    llm_config = _app_config.get("llm", {})
    api_key = os.getenv(llm_config.get("api_key_env", "LLM_API_KEY"))
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        try:
            client = CloudLLMClient(
                provider=llm_config.get("provider", "openai"),
                model=llm_config.get("model", "gpt-4o-mini"),
                api_key=api_key,
                endpoint=llm_config.get("endpoint", ""),
                temperature=llm_config.get("temperature", 0.8),
                max_tokens=llm_config.get("max_tokens", 512),
            )
            set_llm_client(client)
            logger.info(f"LLM client initialized: {client.model}")
        except Exception as e:
            logger.warning(f"LLM init failed (will retry on demand): {e}")
    else:
        logger.warning("No LLM API key found. Set LLM_API_KEY or OPENAI_API_KEY env var.")


def _init_stt():
    """Configure and initialise the Whisper STT engine."""
    stt_config = _app_config.get("models", {}).get("stt", {})
    model_size = stt_config.get("model", "small")
    device = stt_config.get("device", "cuda")
    compute_type = stt_config.get("compute_type", "float16")

    engine = WhisperSTTEngine(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
    )

    set_stt_engine(engine)
    engine.load()  # may log a warning if it fails


def _init_tts():
    """Configure and initialise the CosyVoice TTS engine."""
    tts_config = _app_config.get("models", {}).get("tts", {})
    model_dir = tts_config.get("model_dir", "./models/cosyvoice")
    device = tts_config.get("device", "cuda")

    # Resolve paths relative to the engine directory
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir_abs = os.path.join(engine_dir, model_dir) if not os.path.isabs(model_dir) else model_dir
    profiles_dir = os.path.join(engine_dir, "..", "voice_profiles")

    engine = CosyVoiceEngine(
        model_dir=model_dir_abs,
        device=device,
        fp16=True,
        profiles_dir=profiles_dir,
    )

    set_tts_engine(engine)

    if engine.load():
        logger.info(
            "TTS engine ready — %d voice profile(s) available",
            len(engine.list_voices()),
        )
    else:
        logger.warning(
            "TTS engine not available. "
            "Run `python scripts/download_tts_model.py` to download the model."
        )


def _init_aligner():
    """Configure and initialise the Wav2Vec2 phoneme aligner."""
    aligner_config = _app_config.get("models", {}).get("aligner", {})
    device = aligner_config.get("device", "cuda")

    aligner = Wav2Vec2Aligner(device=device)
    set_aligner(aligner)

    if aligner.load():
        logger.info("Phoneme aligner ready")
    else:
        logger.warning(
            "Phoneme aligner not available — correction engine will skip alignment. "
            "Run: pip install torchaudio"
        )


# ── Main ──

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=9876,
        reload=True,
        log_level="info",
    )
