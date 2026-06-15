# API: Scoring endpoint

from fastapi import APIRouter, HTTPException

from models.schemas import AudioInput
from core.audio_processor import decode_base64_audio
from core.correction_engine import CorrectionEngine

router = APIRouter(prefix="/api/score", tags=["scoring"])
_engine = CorrectionEngine()


@router.post("")
async def score(req: AudioInput, target_text: str = ""):
    """
    Score user pronunciation against target text.
    """
    try:
        audio = decode_base64_audio(req.data, req.sample_rate)

        # Use correction engine to get detailed scores
        result = _engine.process(
            audio=audio,
            user_text="",  # Will be filled by STT in real flow
            target_text=target_text,
            sample_rate=req.sample_rate,
        )

        return {
            "overall_score": result.overall_score,
            "dimensions": result.dimensions.model_dump(),
            "phoneme_errors": [e.model_dump() for e in result.errors],
            "feedback": result.corrected_text,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
