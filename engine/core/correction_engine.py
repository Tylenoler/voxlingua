# ⭐ Pronunciation Correction Engine — VoxLingua core module
#
# Three-level correction system:
#   mild   (score >= 80) → natural correction in conversation
#   medium (60-80)       → visual correction hint on device
#   severe (< 60)        → interrupt + forced repetition

from typing import Optional
import numpy as np

from models.schemas import (
    CorrectionResult, ScoreDimensions, PhonemeError, CorrectionMode,
)


class PhonemeAligner:
    """Align user speech to phoneme-level timestamps."""

    def align(self, audio: np.ndarray, text: str, sample_rate: int = 16000) -> list[dict]:
        """
        Align audio to phoneme sequence.
        Returns list of {phoneme, start_time, end_time, confidence}

        TODO: Replace stub with Wav2Vec2 + CTC forced alignment
        """
        # Stub: return mock alignment for development
        # Real implementation will use Wav2Vec2ForCTC + tokenizer
        words = text.lower().split()
        phoneme_map = {
            "think": [{"phoneme": "θ", "start": 0.1, "end": 0.15},
                      {"phoneme": "ɪ", "start": 0.15, "end": 0.2},
                      {"phoneme": "ŋ", "start": 0.2, "end": 0.3},
                      {"phoneme": "k", "start": 0.3, "end": 0.35}],
            "thank": [{"phoneme": "θ", "start": 0.1, "end": 0.15},
                      {"phoneme": "æ", "start": 0.15, "end": 0.25},
                      {"phoneme": "ŋ", "start": 0.25, "end": 0.35},
                      {"phoneme": "k", "start": 0.35, "end": 0.4}],
            "the": [{"phoneme": "ð", "start": 0.0, "end": 0.15},
                    {"phoneme": "ə", "start": 0.15, "end": 0.3}],
            "this": [{"phoneme": "ð", "start": 0.0, "end": 0.1},
                     {"phoneme": "ɪ", "start": 0.1, "end": 0.2},
                     {"phoneme": "s", "start": 0.2, "end": 0.3}],
            "going": [{"phoneme": "ɡ", "start": 0.0, "end": 0.1},
                      {"phoneme": "oʊ", "start": 0.1, "end": 0.25},
                      {"phoneme": "ɪ", "start": 0.25, "end": 0.3},
                      {"phoneme": "ŋ", "start": 0.3, "end": 0.4}],
        }

        result = []
        for word in words:
            if word in phoneme_map:
                result.extend(phoneme_map[word])
            else:
                # Generic phoneme estimation
                for i, char in enumerate(word[:4]):
                    result.append({
                        "phoneme": char,
                        "start": i * 0.08,
                        "end": (i + 1) * 0.08,
                        "confidence": 0.5,
                    })
        return result


class AccentComparator:
    """Compare user phoneme features against target accent."""

    def compare(
        self,
        user_phonemes: list[dict],
        target_text: str,
    ) -> list[dict]:
        """
        Compare each user phoneme to target accent reference.

        Returns list of {phoneme, expected, actual, score, severity, feedback}

        TODO: Replace stub with real MFCC/F0/Formant comparison
              using the NYC accent voice profile as reference
        """
        # Common ESL pronunciation error patterns for NYC accent
        common_errors = {
            "θ": {"common_mis": "s", "score": 55.0, "feedback":
                  "Place your tongue between your teeth and blow gently"},
            "ð": {"common_mis": "d", "score": 50.0, "feedback":
                  "Vibrate your vocal cords with tongue between teeth"},
            "ŋ": {"common_mis": "n", "score": 65.0, "feedback":
                  "The sound comes from the back of your throat, like 'sing'"},
            "r": {"common_mis": "l", "score": 60.0, "feedback":
                  "Curl your tongue back without touching the roof"},
        }

        results = []
        for phoneme_info in user_phonemes:
            p = phoneme_info["phoneme"]
            conf = phoneme_info.get("confidence", 0.5)

            if p in common_errors:
                err = common_errors[p]
                score = err["score"] * conf
                severity = self._classify_severity(score)
                results.append({
                    "phoneme": p,
                    "expected": p,
                    "actual": err["common_mis"],
                    "score": score,
                    "severity": severity,
                    "feedback": err["feedback"],
                })
            else:
                results.append({
                    "phoneme": p,
                    "expected": p,
                    "actual": p,
                    "score": 92.0 * conf,
                    "severity": "none",
                    "feedback": "",
                })

        return results

    def _classify_severity(self, score: float) -> str:
        if score >= 80:
            return "mild"
        elif score >= 60:
            return "medium"
        else:
            return "severe"


class CorrectionEngine:
    """
    Main correction pipeline.

    Flow:
      user_audio → STT text → phoneme alignment →
      accent comparison → feedback generation
    """

    def __init__(self):
        self.aligner = PhonemeAligner()
        self.comparator = AccentComparator()

    def process(
        self,
        audio: np.ndarray,
        user_text: str,
        target_text: str,
        sample_rate: int = 16000,
        mode: CorrectionMode = None,
    ) -> CorrectionResult:
        """Process user audio and generate correction feedback."""
        if mode is None:
            mode = CorrectionMode()

        # Step 1: Phoneme alignment
        user_phonemes = self.aligner.align(audio, user_text, sample_rate)

        # Step 2: Accent comparison
        comparisons = self.comparator.compare(user_phonemes, target_text)

        # Step 3: Calculate scores
        scores = [c["score"] for c in comparisons if c["severity"] != "none"]
        phoneme_score = np.mean([c["score"] for c in comparisons]) if comparisons else 0.0

        # Step 4: Classify errors
        errors = []
        for c in comparisons:
            if c["severity"] != "none":
                errors.append(PhonemeError(
                    phoneme=c["phoneme"],
                    expected=c["expected"],
                    actual=c["actual"],
                    word=self._find_word(c["phoneme"], target_text),
                    severity=c["severity"],
                    feedback=c["feedback"],
                ))

        # Step 5: Determine correction level
        overall_level = self._determine_level(
            phoneme_score, errors, mode
        )

        # Step 6: Build feedback text
        corrected_text = self._generate_corrected_text(
            user_text, errors
        )

        dimensions = ScoreDimensions(
            phoneme_accuracy=round(phoneme_score, 1),
            fluency=self._estimate_fluency(audio, user_text),
            prosody=self._estimate_prosody(audio),
            completeness=self._estimate_completeness(user_text, target_text),
        )

        return CorrectionResult(
            level=overall_level,
            user_text=user_text,
            corrected_text=corrected_text,
            errors=errors,
            overall_score=round(phoneme_score, 1),
            dimensions=dimensions,
        )

    def _determine_level(self, score: float, errors: list, mode: CorrectionMode) -> str:
        """Determine correction level based on score and mode settings."""
        if mode.mode == "off":
            return "mild"

        severe_errors = [e for e in errors if e.severity == "severe"]
        medium_errors = [e for e in errors if e.severity == "medium"]

        if severe_errors and mode.mode == "all" and mode.interrupt_on_severe:
            return "severe"
        if medium_errors and mode.mode in ("medium", "all"):
            return "medium"
        if mode.mode in ("mild_only", "medium", "all"):
            return "mild"
        return "mild"

    def _find_word(self, phoneme: str, text: str) -> str:
        """Find which word a phoneme belongs to (simplified)."""
        # Stub: return first word containing the phoneme
        return text.split()[0] if text else ""

    def _generate_corrected_text(self, user_text: str, errors: list) -> str:
        """Generate corrected version of user's text."""
        # Stub: simple replacement
        # Real implementation will use phoneme-to-character mapping
        return user_text

    def _estimate_fluency(self, audio: np.ndarray, text: str) -> float:
        """Estimate fluency based on speaking rate and pauses."""
        # Stub: return mock value
        duration = len(audio) / 16000 if len(audio) > 0 else 1
        word_count = len(text.split())
        wpm = (word_count / duration) * 60 if duration > 0 else 0
        # Target: 140-160 wpm for conversational English
        if 100 <= wpm <= 180:
            return 85.0
        elif 80 <= wpm <= 200:
            return 70.0
        else:
            return 55.0

    def _estimate_prosody(self, audio: np.ndarray) -> float:
        """Estimate prosody (intonation pattern) quality."""
        # Stub: return mock value
        # Real implementation will analyze F0 contour
        return 75.0

    def _estimate_completeness(self, user_text: str, target_text: str) -> float:
        """Estimate how many words/ phonemes were completed."""
        if not target_text:
            return 100.0
        user_words = set(user_text.lower().split())
        target_words = set(target_text.lower().split())
        if not target_words:
            return 100.0
        overlap = len(user_words & target_words)
        return round((overlap / len(target_words)) * 100, 1)
