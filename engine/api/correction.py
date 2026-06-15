# API: Pronunciation correction endpoint

from fastapi import APIRouter, HTTPException

from models.schemas import AudioInput, CorrectionMode
from core.audio_processor import decode_base64_audio
from core.correction_engine import CorrectionEngine

router = APIRouter(prefix="/api/correct", tags=["correction"])
_engine = CorrectionEngine()


@router.post("")
async def correct(
    req: AudioInput,
    target_text: str = "",
    mode: str = "medium",
    interrupt_on_severe: bool = True,
):
    """
    Run full correction pipeline on user audio.

    Returns correction result with phoneme-level errors, scores, and feedback.
    """
    try:
        audio = decode_base64_audio(req.data, req.sample_rate)

        correction_mode = CorrectionMode(
            mode=mode,
            interrupt_on_severe=interrupt_on_severe,
        )

        result = _engine.process(
            audio=audio,
            user_text="",  # STT result in production
            target_text=target_text,
            sample_rate=req.sample_rate,
            mode=correction_mode,
        )

        return result.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
