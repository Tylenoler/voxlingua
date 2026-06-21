"""
Conversation pipeline — orchestrates STT → LLM → TTS → Correction

Audio flow:
  user_audio_in → Whisper STT (transcription + phonemes + prosody)
                → LLM (natural response)
                → CosyVoice TTS (streaming, voice-cloned)
                → CorrectionEngine (phoneme comparison + scoring)
                → audio_out + correction_feedback
"""

import logging
from typing import Optional

import numpy as np

from core.audio_processor import decode_base64_audio, encode_pcm_f32le, chunk_audio
from core.correction_engine import CorrectionEngine
from core.session_manager import session_manager
from llm.cloud import get_llm_client
from models.model_manager import get_model
from stt.whisper_stt import WhisperSTT
from tts.cosyvoice_tts import CosyVoiceTTS

logger = logging.getLogger("voxlingua.pipeline")


class ConversationPipeline:
    """
    Orchestrates the full conversation loop:

    audio_in → Whisper STT → LLM → CosyVoice TTS (streaming) → audio_out
                                └→ CorrectionEngine → correction_feedback
    """

    def __init__(self):
        self.correction = CorrectionEngine()
        self._stt: Optional[WhisperSTT] = None
        self._tts: Optional[CosyVoiceTTS] = None

    # ── Lazy model loading ──

    @property
    def stt(self) -> WhisperSTT:
        if self._stt is None:
            try:
                self._stt = get_model("stt")  # type: ignore[assignment]
            except RuntimeError:
                logger.info("Lazy-loading STT model...")
                self._stt = WhisperSTT(model_size="large")
                set_model("stt", self._stt)
        return self._stt

    @property
    def tts(self) -> CosyVoiceTTS:
        if self._tts is None:
            try:
                self._tts = get_model("tts")  # type: ignore[assignment]
            except RuntimeError:
                logger.info("Lazy-loading TTS model...")
                self._tts = CosyVoiceTTS()
                set_model("tts", self._tts)
        return self._tts

    # ── Main processing ──

    def process_audio(
        self,
        session_id: str,
        audio_b64: str,
        audio_format: str = "opus",
        sample_rate: int = 16000,
    ) -> dict:
        """
        Process incoming user audio and generate reply + correction.

        Full pipeline:
          1. Decode audio
          2. Whisper STT → text + phonemes + prosody
          3. Add user message to history
          4. LLM → natural reply
          5. Add assistant message to history
          6. CosyVoice TTS → streamed audio
          7. CorrectionEngine → phoneme-level feedback
          8. Return streamed audio + correction

        Returns:
            dict with keys:
                session_id: str
                stream: list of audio chunk messages
                reply_text: str
                correction: CorrectionResult dict or None
                stt_result: dict with phonemes/prosody (for debug/display)
        """
        session = session_manager.get_session(session_id)
        if not session:
            return {"error": "Session not found or expired"}

        # 1. Decode audio
        audio = decode_base64_audio(audio_b64, sample_rate)

        # 2. STT with phoneme recognition
        try:
            stt_result = self.stt.transcribe_with_phonemes(audio, language=session.language)
            user_text = stt_result["text"]
            user_phonemes = stt_result["phonemes"]
            prosody = stt_result["prosody"]
        except Exception as e:
            logger.error(f"STT failed: {e}")
            return {"error": f"Speech recognition failed: {e}"}

        if not user_text.strip():
            return {
                "session_id": session_id,
                "stream": [],
                "reply_text": "",
                "correction": None,
                "stt_result": stt_result,
            }

        # 3. Add user message
        session.add_message("user", user_text)

        # 4. LLM chat
        try:
            history = session.get_history()
            reply_text = get_llm_client().chat(history, scene=session.scene)
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            reply_text = "Sorry, I couldn't process that. Could you try again?"

        # 5. Add assistant reply
        session.add_message("assistant", reply_text)

        # 6. TTS with voice cloning
        try:
            reply_audio = self.tts.synthesize(reply_text, session.voice_profile)
        except Exception as e:
            logger.warning(f"TTS failed, using fallback: {e}")
            # Fallback: silence
            est_duration = max(len(reply_text.split()) * 0.3, 1.0)
            reply_audio = np.zeros(int(est_duration * 24000), dtype=np.float32)

        # 7. Correction engine — compare user phonemes against expected
        correction = self.correction.process(
            audio=audio,
            user_text=user_text,
            target_text=reply_text,
            user_phonemes=user_phonemes,
            prosody=prosody,
            mode=session.correction_mode,
        )

        # 8. Chunk audio for streaming
        chunks = chunk_audio(reply_audio, chunk_size_ms=200, sample_rate=24000)

        stream_messages = []
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            encoded = encode_pcm_f32le(chunk, 24000)
            if i == 0:
                msg = {
                    "type": "audio_stream_start",
                    "payload": {
                        "session_id": session_id,
                        "total_chunks": total,
                        "format": "pcm_f32le",
                        "sample_rate": 24000,
                        "text": reply_text,
                        "chunk_index": i,
                        "data": encoded,
                    },
                }
            elif i == total - 1:
                msg = {
                    "type": "audio_stream_end",
                    "payload": {
                        "session_id": session_id,
                        "chunk_index": i,
                        "text": reply_text,
                        "full_text": reply_text,
                        "data": encoded,
                    },
                }
            else:
                msg = {
                    "type": "audio_stream_chunk",
                    "payload": {
                        "session_id": session_id,
                        "chunk_index": i,
                        "data": encoded,
                    },
                }
            stream_messages.append(msg)

        return {
            "session_id": session_id,
            "stream": stream_messages,
            "reply_text": reply_text,
            "correction": correction.model_dump() if correction else None,
            "stt_result": {
                "text": user_text,
                "phonemes": user_phonemes[:20] if user_phonemes else [],  # Limit for WS message
                "prosody": prosody,
            },
        }
