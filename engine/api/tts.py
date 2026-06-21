"""
API: TTS endpoint
Synthesize speech using Edge TTS (primary) with CosyVoice 3 fallback.
"""

from fastapi import APIRouter, HTTPException, Response
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
    Synthesize text to speech using TTS engine with voice profile.

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


@router.post("/play")
async def synthesize_and_play(req: TTSRequest):
    """
    Synthesize text to speech and return raw PCM f32le audio.

    Returns raw audio data that browsers can play via AudioContext.
    """
    try:
        model = get_tts()
        audio = model.synthesize(req.text, req.voice_profile)

        # Convert float32 [-1, 1] to int16 WAV for browser playback
        import io
        import struct
        import wave

        sample_rate = 24000
        buf = io.BytesIO()

        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            # Convert float32 to int16
            audio_int16 = (audio * 32767).astype("int16")
            wf.writeframes(audio_int16.tobytes())

        wav_bytes = buf.getvalue()

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'inline; filename="voxlingua_{hash(req.text)}.wav"',
            },
        )
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
@router.get("/voices")
async def list_voices():
    """List all available voice profiles (Edge TTS + CosyVoice)."""
    model = get_tts()
    voices = model.list_profiles()
    return {
        "voices": voices,
        "default": "new_york",
    }
