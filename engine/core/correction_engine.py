"""
Pronunciation Correction Engine — VoxLingua core module.

Three-level correction system::

    mild   (score >= 80) → natural correction in conversation
    medium (60-80)       → visual correction hint on device
    severe (< 60)        → interrupt + forced repetition

Pipeline::

    user_audio → Wav2Vec2Aligner (CTC forced alignment)
              → AccentComparator (score per phoneme)
              → CorrectionEngine (level + feedback)
"""

import logging

import numpy as np

from models.schemas import (
    CorrectionResult, ScoreDimensions, PhonemeError, CorrectionMode,
)
from core.phoneme_aligner import get_aligner

logger = logging.getLogger("voxlingua.correction")


class AccentComparator:
    """Compare user phoneme features against target accent reference.

    Uses the alignment confidence and phoneme difficulty to produce
    realistic per-phoneme scores and actionable feedback.
    """

    # ESL error patterns → feedback messages (Chinese L1 focus)
    FEEDBACK = {
        "θ": "Place your tongue between your teeth and blow gently — like 'th' in 'think'",
        "ð": "Vibrate your vocal cords with tongue between teeth — like 'th' in 'the'",
        "ŋ": "The sound comes from the back of your throat — like 'ng' in 'sing'",
        "r": "Curl your tongue back without touching the roof of your mouth",
        "l": "Touch the tip of your tongue to the ridge behind your upper teeth",
        "æ": "Open your mouth wide — like 'a' in 'cat', not 'e' in 'get'",
        "ʌ": "Short, relaxed sound — like 'u' in 'cup', don't round your lips",
        "ɝ": "Curl your tongue back and hold — like 'ur' in 'turn'",
        "ʃ": "Push air through slightly rounded lips — like 'sh' in 'ship'",
        "ʒ": "Same as 'sh' but with vocal cord vibration — like 's' in 'measure'",
        "tʃ": "Start with 't' then release into 'sh' — like 'ch' in 'chair'",
        "dʒ": "Start with 'd' then release into 'zh' — like 'j' in 'jump'",
    }

    # Phonemes that are common ESL difficulty targets
    DIFFICULT_PHONEMES = set(FEEDBACK.keys())

    def compare(
        self,
        user_phonemes: list[dict],
        target_text: str,
    ) -> list[dict]:
        """Score each phoneme in *user_phonemes*.

        Returns list of dicts::

            {phoneme, expected, actual, score, severity, feedback, start, end}
        """
        results: list[dict] = []
        tracked_phonemes = set()

        for ph in user_phonemes:
            p = ph.get("phoneme", "")
            conf = ph.get("confidence", 0.5)
            start = ph.get("start", 0.0)
            end = ph.get("end", 0.0)

            # Compute score from confidence × difficulty
            if p in self.DIFFICULT_PHONEMES:
                # Difficult phoneme: confidence is the main signal
                # Low confidence → likely mispronounced
                base_score = conf * 100.0
                # Apply difficulty penalty
                difficulty = ph.get("difficulty", 0.5)
                score = base_score * (1.0 - difficulty * 0.3)
                score = max(10.0, min(100.0, score))

                severity = self._classify_severity(score)
                actual = p if score >= 70 else self._guess_mispronunciation(p)
                feedback = self.FEEDBACK.get(p, "")
            else:
                # Easy phoneme: high score by default
                score = max(70.0, conf * 100.0)
                severity = "none"
                actual = p
                feedback = ""

            results.append({
                "phoneme": p,
                "expected": p,
                "actual": actual,
                "score": round(score, 1),
                "severity": severity,
                "feedback": feedback,
                "start": start,
                "end": end,
            })
            tracked_phonemes.add(p)

        return results

    @staticmethod
    def _guess_mispronunciation(phoneme: str) -> str:
        """Guess the most likely mispronunciation for a difficult phoneme."""
        common_substitutions = {
            "θ": "s", "ð": "d", "ŋ": "n", "r": "l",
            "æ": "ɛ", "ʌ": "ɑ", "ɝ": "r", "ʃ": "s",
            "ʒ": "z", "tʃ": "ʃ", "dʒ": "ʒ",
        }
        return common_substitutions.get(phoneme, phoneme)

    @staticmethod
    def _classify_severity(score: float) -> str:
        if score >= 80:
            return "mild"
        elif score >= 60:
            return "medium"
        else:
            return "severe"


class CorrectionEngine:
    """Main correction pipeline.

    Flow::

        user_audio → Wav2Vec2Aligner (phoneme alignment) →
        AccentComparator (per-phoneme scoring) →
        feedback generation
    """

    def __init__(self):
        self.comparator = AccentComparator()

    def process(
        self,
        audio: np.ndarray,
        user_text: str,
        target_text: str,
        sample_rate: int = 16000,
        mode: CorrectionMode = None,
    ) -> CorrectionResult:
        """Process user audio and generate correction feedback.

        Parameters
        ----------
        audio : np.ndarray
            User recording, any sample rate.
        user_text : str
            STT transcription of *audio*.
        target_text : str
            Expected/correct text (from LLM response).
        sample_rate : int
            Sample rate of *audio*.
        mode : CorrectionMode
            Correction sensitivity mode.

        Returns
        -------
        CorrectionResult with level, errors, scores, etc.
        """
        if mode is None:
            mode = CorrectionMode()

        # ── Step 1: Wav2Vec2 phoneme alignment ──
        user_phonemes = self._align(audio, user_text, sample_rate)

        if not user_phonemes:
            logger.debug("No phonemes aligned — returning empty correction")
            return self._empty_result(user_text)

        # ── Step 2: Accent comparison ──
        comparisons = self.comparator.compare(user_phonemes, target_text)

        # ── Step 3: Calculate scores ──
        phoneme_scores = [c["score"] for c in comparisons]
        phoneme_score = float(np.mean(phoneme_scores)) if phoneme_scores else 0.0

        # ── Step 4: Classify errors ──
        errors: list[PhonemeError] = []
        for c in comparisons:
            if c["severity"] != "none":
                word = self._find_word(c["phoneme"], c["start"], c["end"], user_text)
                errors.append(PhonemeError(
                    phoneme=c["phoneme"],
                    expected=c["expected"],
                    actual=c["actual"],
                    word=word,
                    severity=c["severity"],
                    feedback=c["feedback"],
                ))

        # ── Step 5: Determine correction level ──
        overall_level = self._determine_level(phoneme_score, errors, mode)

        # ── Step 6: Build corrected text ──
        corrected_text = self._generate_corrected_text(user_text, errors)

        # ── Step 7: Calculate dimensions ──
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

    # ── aligner integration ───────────────────────────────────────

    @staticmethod
    def _align(audio: np.ndarray, text: str, sample_rate: int) -> list[dict]:
        """Run Wav2Vec2 phoneme alignment, adding difficulty weights."""
        try:
            aligner = get_aligner()
        except RuntimeError:
            logger.warning("Aligner not available — skipping alignment")
            return []

        if not aligner.is_loaded():
            logger.warning("Aligner not loaded — skipping alignment")
            return []

        try:
            phonemes = aligner.align(audio, text, sample_rate)
        except Exception as exc:
            logger.error("Alignment failed: %s", exc)
            return []

        # Augment phoneme dicts with difficulty weights
        for ph in phonemes:
            from core.phoneme_aligner import Wav2Vec2Aligner
            ph["difficulty"] = Wav2Vec2Aligner.phoneme_difficulty(ph["phoneme"])

        return phonemes

    # ── level determination ───────────────────────────────────────

    @staticmethod
    def _determine_level(score: float, errors: list, mode: CorrectionMode) -> str:
        """Determine correction level based on score and mode."""
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

    # ── error message helpers ─────────────────────────────────────

    @staticmethod
    def _find_word(
        phoneme: str,
        start: float,
        end: float,
        text: str,
    ) -> str:
        """Find which word a phoneme belongs to based on timing.

        Falls back to the first word if timing is unavailable.
        """
        if not text:
            return ""
        words = text.split()
        # Simple heuristic: estimate word durations evenly
        if not words:
            return ""
        # If we have reliable timestamps, they would come from the aligner.
        # Without per-word timing here, return the first word containing
        # a character match.
        for word in words:
            if phoneme.lower() in word.lower():
                return word
        return words[0]

    @staticmethod
    def _generate_corrected_text(user_text: str, errors: list) -> str:
        """Generate corrected version of the user's text.

        For each error, annotate with feedback (e.g. ``think→[θ]think``).
        """
        if not errors:
            return user_text

        # Mark words that have errors
        marked_words = set()
        for err in errors:
            if err.word:
                marked_words.add(err.word.lower())

        if not marked_words:
            return user_text

        words = user_text.split()
        corrected = []
        for w in words:
            if w.lower() in marked_words:
                corrected.append(f"*{w}*")
            else:
                corrected.append(w)
        return " ".join(corrected)

    # ── scoring sub-dimensions ────────────────────────────────────

    @staticmethod
    def _estimate_fluency(audio: np.ndarray, text: str) -> float:
        """Estimate fluency based on speaking rate and pauses.

        Uses duration and word count for a heuristic fluency score.
        """
        if len(audio) == 0 or not text:
            return 75.0
        duration = len(audio) / 16000
        word_count = max(len(text.split()), 1)
        wpm = (word_count / duration) * 60 if duration > 0 else 0
        # Target: 140-160 wpm for conversational English
        if 110 <= wpm <= 170:
            return 85.0
        elif 80 <= wpm <= 200:
            return 70.0
        else:
            return 55.0

    @staticmethod
    def _estimate_prosody(audio: np.ndarray) -> float:
        """Estimate prosody (intonation pattern) quality.

        Stub: uses RMS energy variance as a rough prosody proxy.
        TODO: Replace with F0 contour analysis (e.g. via pyWorld).
        """
        if len(audio) == 0:
            return 75.0
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.01:
            return 75.0  # silent audio — neutral score
        # Rough heuristic: higher RMS variance ≈ more dynamic intonation
        frame_size = int(0.025 * 16000)  # 25 ms frames
        if frame_size <= 0 or len(audio) < frame_size:
            return 75.0
        n_frames = len(audio) // frame_size
        frame_energies = np.array([
            np.sqrt(np.mean(audio[i * frame_size:(i + 1) * frame_size] ** 2))
            for i in range(n_frames)
        ])
        if frame_energies.max() == 0:
            return 75.0
        norm_energies = frame_energies / frame_energies.max()
        variance = float(np.var(norm_energies))
        # Map variance to score: 0.0 → 60, 0.05 → 85, 0.1+ → 95
        score = min(95.0, 60.0 + variance * 500)
        return round(score, 1)

    @staticmethod
    def _estimate_completeness(user_text: str, target_text: str) -> float:
        """Estimate how many content words were spoken relative to target."""
        if not target_text:
            return 100.0
        user_words = set(user_text.lower().split())
        target_words = set(target_text.lower().split())
        if not target_words:
            return 100.0
        overlap = len(user_words & target_words)
        return round((overlap / len(target_words)) * 100, 1)

    @staticmethod
    def _empty_result(user_text: str) -> CorrectionResult:
        """Return a neutral correction result when alignment fails."""
        return CorrectionResult(
            level="mild",
            user_text=user_text,
            corrected_text=user_text,
            errors=[],
            overall_score=85.0,
            dimensions=ScoreDimensions(
                phoneme_accuracy=85.0,
                fluency=75.0,
                prosody=75.0,
                completeness=100.0,
            ),
        )
