"""
API: TTS endpoint
Synthesize speech using CosyVoice 3 with voice cloning.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.audio_processor import encode_pcm_f32le
from tts.cosyvoice_tts import CosyVoiceTTS

router = APIRouter(prefix="/api/tts", tags=["tts"])

_tts_model: CosyVoiceTTS | None = None


def get_tts():
    global _tts_model
    if _tts_model is None:
        _tts_model = CosyVoiceTTS()
    return _tts_model


class TTSRequest(BaseModel):
    text: str
    voice_profile: str = "new_york"
    stream: bool = False


@router.post("")
async def synthesize(req: TTSRequest):
    """
    Synthesize text to speech using CosyVoice 3 with voice profile.

    Args:
        req: TTSRequest with text and voice_profile

    Returns:
        dict with base64-encoded PCM f32le audio data
    """
    try:
        model = get_tts()
        audio = model.synthesize(req.text, req.voice_profile)
        sample_rate = 24000

        encoded = encode_pcm_f32le(audio, sample_rate)

        return {
            "format": "pcm_f32le",
            "sample_rate": sample_rate,
            "data": encoded,
            "text": req.text,
            "language": "en",
            "duration_sec": round(len(audio) / sample_rate, 2),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles")
async def list_profiles():
    """List available voice profiles."""
    try:
        model = get_tts()
        return {"profiles": model.list_profiles()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
