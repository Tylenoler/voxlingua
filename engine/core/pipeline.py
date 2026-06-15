# Conversation pipeline — orchestrates STT → LLM → TTS → Correction

from typing import Optional
import numpy as np

from core.session_manager import session_manager, Session
from core.correction_engine import CorrectionEngine
from core.audio_processor import decode_base64_audio, encode_pcm_f32le, chunk_audio
from llm.cloud import get_llm_client


class ConversationPipeline:
    """
    Orchestrates the full conversation loop:

    audio_in → STT → LLM → TTS (streaming) → audio_out
                                          └→ CorrectionEngine → correction
    """

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

        Returns:
            {
                "reply_audio": [chunked audio stream messages],
                "reply_text": "...",
                "correction": CorrectionResult or None,
            }
        """
        session = session_manager.get_session(session_id)
        if not session:
            return {"error": "Session not found or expired"}

        # 1. Decode audio
        audio = decode_base64_audio(audio_b64, sample_rate)

        # 2. STT (stub - real Whisper will be integrated separately)
        user_text = self._stt(audio)

        # 3. Add to conversation history
        session.add_message("user", user_text)

        # 4. LLM chat
        history = session.get_history()
        reply_text = get_llm_client().chat(history, scene=session.scene)

        # 5. Add reply to history
        session.add_message("assistant", reply_text)

        # 6. TTS (stub - real CosyVoice will be integrated separately)
        reply_audio = self._tts(reply_text, session.voice_profile)

        # 7. Correction engine
        correction = self.correction.process(
            audio=audio,
            user_text=user_text,
            target_text=reply_text,
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
        }

    def _stt(self, audio: np.ndarray) -> str:
        """
        Speech-to-text using Whisper.

        TODO: Replace stub with real Whisper inference.
        """
        return "I think this is a good idea."

    def _tts(self, text: str, voice_profile: str = "new_york") -> np.ndarray:
        """
        Text-to-speech using CosyVoice with voice profile.

        TODO: Replace stub with real CosyVoice streaming inference.
        """
        # Stub: generate silent audio of estimated duration
        estimated_duration = len(text.split()) * 0.3  # ~300ms per word
        sample_rate = 24000
        num_samples = int(estimated_duration * sample_rate)
        return np.zeros(num_samples, dtype=np.float32)
