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
import asyncio
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
from llm.cloud import CloudLLMClient, set_llm_client

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


# ── REST Endpoints ──

@app.get("/api/status")
async def get_status():
    """Get engine status."""
    llm_available = False
    try:
        from llm.cloud import get_llm_client
        llm_available = get_llm_client().is_available()
    except Exception:
        pass

    return {
        "status": "running",
        "version": "1.0.0",
        "llm_connected": llm_available,
        "active_sessions": session_manager.active_count,
        "connected_devices": len(_ws_connections),
    }


@app.get("/api/voices")
async def list_voices():
    """List available voice profiles."""
    # TODO: Read from voice_profiles directory
    return {
        "voices": [
            {
                "profile_id": "new_york",
                "name": "New York Accent (default)",
                "language": "en",
                "is_default": True,
            }
        ]
    }


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
            config = yaml.safe_load(f)
        logger.info(f"Config loaded from {config_path}")

        # Initialize LLM client
        llm_config = config.get("llm", {})
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

    logger.info("Engine ready. Listening on port 9876...")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down VoxLingua engine...")


# ── Main ──

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=9876,
        reload=True,
        log_level="info",
    )
