"""
API: STT endpoint
Transcribe audio to text using Whisper with phoneme-level recognition.
"""

from fastapi import APIRouter, HTTPException

from core.audio_processor import decode_base64_audio
from models.schemas import AudioInput
from stt.whisper_stt import WhisperSTT

router = APIRouter(prefix="/api/stt", tags=["stt"])

# Lazy-loaded global STT model
_stt_model: WhisperSTT | None = None


def get_stt():
    global _stt_model
    if _stt_model is None:
        _stt_model = WhisperSTT(model_size="large")
    return _stt_model


@router.post("")
async def transcribe(req: AudioInput, phonemes: bool = False):
    """
    Transcribe audio to text using Whisper.

    Args:
        req: AudioInput with base64-encoded audio
        phonemes: If True, also return phoneme-level alignment and prosody

    Returns:
        dict with text, language, duration, and optionally phonemes + prosody
    """
    try:
        audio = decode_base64_audio(req.data, req.sample_rate)
        model = get_stt()

        if phonemes:
            result = model.transcribe_with_phonemes(audio)
            return {
                "session_id": req.session_id,
                "text": result["text"],
                "language": "en",
                "duration_sec": float(len(audio)) / req.sample_rate,
                "phonemes": result["phonemes"][:50],
                "prosody": result["prosody"],
                "words": result["words"],
            }
        else:
            result = model.transcribe(audio, word_timestamps=True)
            return {
                "session_id": req.session_id,
                "text": result["text"],
                "language": result["language"],
                "duration_sec": result["duration_sec"],
                "segments": result["segments"],
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
