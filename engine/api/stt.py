# API: STT endpoint

from fastapi import APIRouter, HTTPException

from models.schemas import AudioInput
from core.audio_processor import decode_base64_audio

router = APIRouter(prefix="/api/stt", tags=["stt"])


# TODO: Initialize Whisper model globally
# import whisper
# _whisper_model = None
#
# def get_stt_model():
#     global _whisper_model
#     if _whisper_model is None:
#         _whisper_model = whisper.load_model("small")
#     return _whisper_model


@router.post("")
async def transcribe(req: AudioInput):
    """
    Transcribe audio to text using Whisper.
    """
    try:
        audio = decode_base64_audio(req.data, req.sample_rate)

        # TODO: Replace with real Whisper inference
        # model = get_stt_model()
        # result = model.transcribe(audio)
        # text = result["text"].strip()

        text = "I think this is a good idea."  # stub

        return {
            "session_id": req.session_id,
            "text": text,
            "language": "en",
            "duration_sec": float(len(audio)) / req.sample_rate,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
