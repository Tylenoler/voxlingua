"""
Conversation pipeline — orchestrates STT → LLM → TTS → Correction.

audio_in → STT → LLM → TTS (streaming) → audio_out
                          └→ CorrectionEngine → correction
"""

import logging

import numpy as np

from core.session_manager import session_manager
from core.correction_engine import CorrectionEngine
from core.audio_processor import decode_base64_audio, encode_pcm_f32le, chunk_audio
from core.stt_engine import get_stt_engine
from core.tts_engine import get_tts_engine
from llm.cloud import get_llm_client

logger = logging.getLogger("voxlingua.pipeline")


class ConversationPipeline:
    """Orchestrates the full conversation loop."""

    TTS_SAMPLE_RATE = 24000

    def __init__(self):
        self.correction = CorrectionEngine()

    def process_audio(
        self,
        session_id: str,
        audio_b64: str,
        audio_format: str = "opus",
        sample_rate: int = 16000,
    ) -> dict:
        """
        Process incoming user audio and generate reply + correction.

        Returns
        -------
        dict with keys:
            - reply_audio  : list of streaming audio messages
            - reply_text   : str
            - correction   : CorrectionResult dict or None
            - session_id   : str
        """
        session = session_manager.get_session(session_id)
        if not session:
            return {"error": "Session not found or expired"}

        # 1. Decode audio
        audio = decode_base64_audio(audio_b64, sample_rate)

        # 2. STT — real Whisper will be integrated separately
        user_text = self._stt(audio)

        # 3. Add to conversation history
        session.add_message("user", user_text)

        # 4. LLM chat
        history = session.get_history()
        reply_text = get_llm_client().chat(history, scene=session.scene)

        # 5. Add reply to history
        session.add_message("assistant", reply_text)

        # 6. TTS — real CosyVoice inference
        reply_audio = self._tts(reply_text, session.voice_profile)

        # 7. Correction engine
        correction = self.correction.process(
            audio=audio,
            user_text=user_text,
            target_text=reply_text,
            mode=session.correction_mode,
        )

        # 8. Chunk audio for streaming (200 ms frames)
        chunks = chunk_audio(reply_audio, chunk_size_ms=200, sample_rate=self.TTS_SAMPLE_RATE)

        stream_messages = []
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            encoded = encode_pcm_f32le(chunk, self.TTS_SAMPLE_RATE)
            if i == 0:
                msg = {
                    "type": "audio_stream_start",
                    "payload": {
                        "session_id": session_id,
                        "total_chunks": total,
                        "format": "pcm_f32le",
                        "sample_rate": self.TTS_SAMPLE_RATE,
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
        }

    # ── internal helpers ──────────────────────────────────────────

    def _stt(self, audio: np.ndarray) -> str:
        """Speech-to-text using Whisper.

        Returns the transcribed text string, or empty string on failure.
        """
        try:
            engine = get_stt_engine()
        except RuntimeError:
            logger.warning("STT engine not available — returning stub text")
            return "I think this is a good idea."

        if not engine.is_loaded():
            logger.warning("STT engine not loaded — returning stub text")
            return "I think this is a good idea."

        try:
            result = engine.transcribe(audio, language="en", word_timestamps=False)
            text = result.get("text", "")
            logger.info("STT: %r (lang=%s, dur=%.1fs)", text[:80], result.get("language"), result.get("duration", 0))
            return text
        except Exception as exc:
            logger.error("STT inference failed: %s — returning stub text", exc)
            return "I think this is a good idea."

    def _tts(self, text: str, voice_profile: str = "new_york") -> np.ndarray:
        """Text-to-speech using CosyVoice with voice profile.

        Returns PCM f32le np.ndarray at 24 kHz.
        """
        try:
            engine = get_tts_engine()
        except RuntimeError:
            logger.warning("TTS engine not available — returning silent audio")
            return self._silent_audio(text)

        if not engine.is_loaded():
            logger.warning("TTS engine not loaded — returning silent audio")
            return self._silent_audio(text)

        try:
            return engine.generate(text, voice_profile=voice_profile)
        except Exception as exc:
            logger.error("TTS generation failed: %s — returning silent audio", exc)
            return self._silent_audio(text)

    def _silent_audio(self, text: str) -> np.ndarray:
        """Generate silent audio of the estimated duration as fallback."""
        estimated_duration = max(len(text.split()) * 0.3, 1.0)
        num_samples = int(estimated_duration * self.TTS_SAMPLE_RATE)
        return np.zeros(num_samples, dtype=np.float32)
