"""
API: STT endpoint — /api/stt

Transcribes audio to text using the local Whisper model.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import AudioInput
from core.audio_processor import decode_base64_audio
from core.stt_engine import get_stt_engine

router = APIRouter(prefix="/api/stt", tags=["stt"])

__all__ = ["router"]


@router.post("")
async def transcribe(req: AudioInput):
    """
    Transcribe audio to text using Whisper.
    """
    try:
        audio = decode_base64_audio(req.data, req.sample_rate)

        engine = get_stt_engine()
        if not engine.is_loaded():
            raise HTTPException(status_code=503, detail="STT engine not loaded")

        result = engine.transcribe(audio, language="en", word_timestamps=True)

        return {
            "session_id": req.session_id,
            "text": result["text"],
            "language": result["language"],
            "segments": result["segments"],
            "duration_sec": result["duration"],
        }

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
