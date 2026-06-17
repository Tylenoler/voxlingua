"""
API: TTS endpoints — /api/tts

Synthesises text to speech using the CosyVoice TTS engine.
Supports both full-audio and streaming responses.
"""

import json

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse

from core.audio_processor import encode_pcm_f32le
from core.tts_engine import get_tts_engine

router = APIRouter(prefix="/api/tts", tags=["tts"])

__all__ = ["router"]


@router.post("")
async def synthesize(
    text: str = Body(..., min_length=1, max_length=4096),
    voice_profile: str = Body("new_york"),
):
    """Synthesise *text* to speech using the selected *voice_profile*.

    Returns PCM f32le audio at 24 kHz encoded as base64.
    """
    try:
        engine = get_tts_engine()
        audio = engine.generate(text, voice_profile=voice_profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if len(audio) == 0:
        raise HTTPException(status_code=500, detail="TTS generated empty audio")

    encoded = encode_pcm_f32le(audio, engine.SAMPLE_RATE)

    return {
        "format": "pcm_f32le",
        "sample_rate": engine.SAMPLE_RATE,
        "data": encoded,
        "text": text,
        "language": "en",
    }


@router.post("/stream")
async def synthesize_stream(
    text: str = Body(..., min_length=1, max_length=4096),
    voice_profile: str = Body("new_york"),
):
    """Stream TTS audio as a sequence of PCM f32le chunks (server-sent events)."""
    try:
        engine = get_tts_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    async def event_stream():
        meta = json.dumps({
            "type": "tts_meta",
            "format": "pcm_f32le",
            "sample_rate": engine.SAMPLE_RATE,
            "text": text,
        })
        yield f"data: {meta}\n\n"
        for chunk in engine.generate_stream(text, voice_profile=voice_profile):
            encoded = encode_pcm_f32le(chunk, engine.SAMPLE_RATE)
            yield f"data: {json.dumps({'type': 'audio', 'data': encoded})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/voices")
async def list_tts_voices():
    """List all available voice profiles the TTS engine can use."""
    try:
        engine = get_tts_engine()
        voices = engine.list_voices()
    except RuntimeError:
        voices = [
            {
                "profile_id": "new_york",
                "name": "New York Accent (default)",
                "language": "en",
                "method": "zero_shot",
                "is_default": True,
            }
        ]

    return {"voices": voices}
