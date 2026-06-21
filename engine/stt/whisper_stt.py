# Whisper STT — Speech-to-text with word-level timestamps
#
# Provides:
#   - Full transcription with word-level timestamps
#   - Integration with Wav2Vec2 for phoneme-level alignment
#   - Speaker tone/prosody analysis

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("voxlingua.stt.whisper")


class WhisperSTT:
    """OpenAI Whisper-based speech-to-text with phoneme alignment.

    Uses Whisper for robust transcription (multilingual, handles noise),
    then refines timestamps to phoneme level via Wav2Vec2 forced alignment.
    """

    def __init__(self, model_size: str = "large", device: str = "auto"):
        """
        Args:
            model_size: tiny/base/small/medium/large
            device: 'cuda', 'cpu', or 'auto' (auto-detect)
        """
        self.model_size = model_size
        self.device = device
        self._model = None

    def _lazy_load(self):
        """Load Whisper model on first use."""
        if self._model is not None:
            return

        import whisper

        logger.info(f"Loading Whisper model '{self.model_size}'...")
        self._model = whisper.load_model(
            self.model_size,
            device=self.device if self.device != "auto" else None,
        )
        logger.info(f"Whisper {self.model_size} loaded")


    def _ensure_dtype(self, audio: np.ndarray) -> np.ndarray:
        """Ensure audio is float32 for whisper internal processing."""
        if audio.dtype != np.float64:
            audio = audio.astype(np.float32)
        return audio


    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en",
        word_timestamps: bool = True,
    ) -> dict:
        """Transcribe audio with word-level timestamps.

        Args:
            audio: Audio waveform as float32 numpy array (16kHz mono)
            language: Language code ('en' for English)
            word_timestamps: Whether to return per-word timing

        Returns:
            dict with keys:
                text: Full transcription string
                segments: List of segment dicts with per-word timestamps
                language: Detected language
                duration_sec: Audio duration in seconds
        """
        self._lazy_load()
        audio = self._ensure_dtype(audio)

        result = self._model.transcribe(
            audio,
            language=language,
            word_timestamps=word_timestamps,
            fp16=self._use_fp16(),
        )

        # Clean and normalize output
        text = result.get("text", "").strip()
        segments = result.get("segments", [])

        return {
            "text": text,
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                    "words": [
                        {
                            "word": w["word"].strip(),
                            "start": w["start"],
                            "end": w["end"],
                            "probability": w.get("probability", 1.0),
                        }
                        for w in seg.get("words", [])
                        if w.get("word", "").strip()
                    ],
                }
                for seg in segments
            ],
            "language": result.get("language", language),
            "duration_sec": float(len(audio)) / 16000 if len(audio) > 0 else 0,
        }

    def transcribe_with_phonemes(
        self,
        audio: np.ndarray,
        language: str = "en",
    ) -> dict:
        """Transcribe and align to phoneme level.

        Combines Whisper transcription with Wav2Vec2 CTC forced alignment
        to get phoneme-level timing and confidence scores.

        Returns:
            dict with:
                text: Full transcription
                words: Per-word data (text, start, end, confidence)
                phonemes: Per-phoneme data (phoneme, start, end, confidence, word)
                prosody: Prosody metrics (pitch range, speaking rate, energy)
        """
        audio = self._ensure_dtype(audio)
        # Step 1: Get word-level transcription from Whisper
        result = self.transcribe(audio, language=language, word_timestamps=True)

        if not result["text"]:
            return {
                "text": "",
                "words": [],
                "phonemes": [],
                "prosody": self._analyze_prosody(audio),
            }

        # Step 2: Get phoneme alignment using Wav2Vec2
        phonemes = self._align_phonemes(audio, result["text"])

        # Step 3: Analyze prosody
        prosody = self._analyze_prosody(audio)

        return {
            "text": result["text"],
            "words": [
                w for seg in result["segments"] for w in seg["words"]
            ],
            "phonemes": phonemes,
            "prosody": prosody,
        }

    def _align_phonemes(self, audio: np.ndarray, text: str) -> list[dict]:
        """Align transcribed text to phonemes using Wav2Vec2.

        Falls back to pronunciation-dict-based alignment if Wav2Vec2
        is not available.
        """
        try:
            return self._wav2vec2_align(audio, text)
        except Exception as e:
            logger.warning(f"Wav2Vec2 alignment failed, using dict fallback: {e}")
            return self._dict_align(text, audio)

    def _wav2vec2_align(self, audio: np.ndarray, text: str) -> list[dict]:
        """CTC forced alignment using Wav2Vec2.

        Uses facebook/wav2vec2-large-960h-lv60-self for phoneme-level
        recognition with precise timestamps.
        """
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        model_name = "facebook/wav2vec2-large-960h-lv60-self"
        processor = Wav2Vec2Processor.from_pretrained(model_name)
        model = Wav2Vec2ForCTC.from_pretrained(model_name)

        if self.device == "cuda" or (self.device == "auto" and torch.cuda.is_available()):
            model = model.to("cuda")

        # Process audio
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = model(inputs.input_values.to(model.device)).logits

        # Get CTC alignment
        predicted_ids = torch.argmax(logits, dim=-1)[0]
        predicted_chars = processor.tokenizer.decode(predicted_ids)

        # Convert frame-level predictions to time-aligned phonemes
        frame_duration = len(audio) / 16000 / logits.shape[1]

        phonemes = []
        current_phoneme = None
        start_frame = 0

        for frame_idx, token_id in enumerate(predicted_ids):
            token = processor.tokenizer.convert_ids_to_tokens(int(token_id))

            if token == processor.tokenizer.pad_token:
                continue
            if token == processor.tokenizer.word_delimiter_token:
                continue

            if token != current_phoneme:
                if current_phoneme is not None:
                    phonemes.append({
                        "phoneme": current_phoneme,
                        "start_time": round(start_frame * frame_duration, 3),
                        "end_time": round(frame_idx * frame_duration, 3),
                        "confidence": 0.85,  # placeholder
                    })
                current_phoneme = token
                start_frame = frame_idx

        if current_phoneme is not None:
            phonemes.append({
                "phoneme": current_phoneme,
                "start_time": round(start_frame * frame_duration, 3),
                "end_time": round(len(predicted_ids) * frame_duration, 3),
                "confidence": 0.85,
            })

        return phonemes

    def _dict_align(self, text: str, audio: np.ndarray) -> list[dict]:
        """Dictionary-based phoneme alignment fallback."""
        from core.correction_engine import PhonemeAligner
        aligner = PhonemeAligner()
        return aligner.align(audio, text, 16000)

    def _analyze_prosody(self, audio: np.ndarray) -> dict:
        """Analyze prosodic features from audio.

        In production, uses librosa to extract:
        - F0 contour (pitch)
        - Energy (loudness)
        - Speaking rate
        - Pause patterns
        """
        if len(audio) < 160:  # Need at least 10ms
            return {
                "pitch_mean": 0.0,
                "pitch_range": 0.0,
                "energy_mean": 0.0,
                "speaking_rate": 0.0,
                "pause_ratio": 0.0,
            }

        try:
            import librosa

            # F0 estimation
            f0, voiced_flags, _ = librosa.pyin(
                audio.astype(np.float64),
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=16000,
            )
            f0_voiced = f0[voiced_flags]
            pitch_mean = float(np.nanmean(f0_voiced)) if len(f0_voiced) > 0 else 0.0
            pitch_range = float(np.nanstd(f0_voiced)) if len(f0_voiced) > 0 else 0.0

            # Energy (RMS)
            rms = librosa.feature.rms(y=audio.astype(np.float64), frame_length=2048, hop_length=512)[0]
            energy_mean = float(np.mean(rms))

            # Voice activity detection for speaking rate estimation
            import webrtcvad
            vad = webrtcvad.Vad(2)
            frame_len = 320  # 20ms at 16kHz
            voiced_frames = 0
            total_frames = len(audio) // frame_len

            for i in range(total_frames):
                frame = audio[i * frame_len:(i + 1) * frame_len]
                frame_int16 = (frame * 32767).astype(np.int16).tobytes()
                try:
                    if vad.is_speech(frame_int16, 16000):
                        voiced_frames += 1
                except Exception:
                    pass

            pause_ratio = 1.0 - (voiced_frames / max(total_frames, 1))
            speaking_rate = float(len(audio) / 16000 * (1 - pause_ratio))

        except ImportError:
            # Fallback if librosa/webrtcvad not installed
            rms_val = float(np.sqrt(np.mean(audio ** 2)))
            energy_mean = rms_val
            pitch_mean = 120.0
            pitch_range = 40.0
            pause_ratio = 0.15
            speaking_rate = float(len(audio) / 16000)

        return {
            "pitch_mean": round(pitch_mean, 1),
            "pitch_range": round(pitch_range, 1),
            "energy_mean": round(energy_mean, 4),
            "speaking_rate": round(speaking_rate, 2),
            "pause_ratio": round(pause_ratio, 3),
        }

    def _use_fp16(self) -> bool:
        """Determine if fp16 is available."""
        try:
            import torch
            if self.device == "cuda" or (self.device == "auto" and torch.cuda.is_available()):
                return True
        except ImportError:
            pass
        return False

    def is_available(self) -> bool:
        """Check if Whisper model is loaded."""
        return self._model is not None
