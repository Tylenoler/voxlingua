# API: TTS endpoint

from fastapi import APIRouter, HTTPException
import numpy as np

from models.schemas import AudioInput
from core.audio_processor import encode_pcm_f32le

router = APIRouter(prefix="/api/tts", tags=["tts"])


# TODO: Initialize CosyVoice model globally
# from cosyvoice.cli.cosyvoice import CosyVoice
# _cosyvoice = None
#
# def get_tts_model():
#     global _cosyvoice
#     if _cosyvoice is None:
#         _cosyvoice = CosyVoice(cosyvoice_path)
#     return _cosyvoice


@router.post("")
async def synthesize(text: str, voice_profile: str = "new_york"):
    """
    Synthesize text to speech using CosyVoice with voice profile.
    """
    try:
        # TODO: Replace with real CosyVoice inference
        # model = get_tts_model()
        # audio = model.inference(text, voice_profile)
        # text
        # Stub: return silent audio
        sample_rate = 24000
        duration = max(len(text.split()) * 0.3, 1.0)
        num_samples = int(duration * sample_rate)
        audio = np.zeros(num_samples, dtype=np.float32)

        encoded = encode_pcm_f32le(audio, sample_rate)

        return {
            "format": "pcm_f32le",
            "sample_rate": sample_rate,
            "data": encoded,
            "text": text,
            "language": "en",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
