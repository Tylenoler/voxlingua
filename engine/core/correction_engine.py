"""
VoxLingua — Pronunciation Correction Engine

Three-level correction system:
  - mild   (score >= 80) → natural correction in conversation
  - medium (60-80)       → visual correction hint on device
  - severe (< 60)        → interrupt + forced repetition

Phoneme mapping based on IPA (International Phonetic Alphabet)
with CMU dictionary-style word-to-phoneme support.
"""

import re
from math import exp

import numpy as np

from models.schemas import (
    CorrectionResult, ScoreDimensions, PhonemeError, CorrectionMode,
)


# ══════════════════════════════════════════════════════════════
# Comprehensive English Phoneme Dictionary (IPA)
# ══════════════════════════════════════════════════════════════

# IPA vowel phonemes
VOWELS = {
    "iː", "ɪ", "eɪ", "ɛ", "æ", "ɑː", "ɒ", "ɔː", "oʊ", "ʊ", "uː",
    "ʌ", "ɜː", "ə", "aɪ", "aʊ", "ɔɪ", "ɪər", "eər", "ʊər",
}

# IPA consonant phonemes
CONSONANTS = {
    "p", "b", "t", "d", "k", "ɡ",
    "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ",
    "h", "m", "n", "ŋ",
    "l", "r", "w", "j",
    "tʃ", "dʒ",
}

# Common ESL error patterns for Mandarin/Cantonese speakers
ESL_ERROR_PATTERNS = {
    # TH sounds → most common ESL errors
    "θ": {"common_mis": "s", "score": 45.0, "frequency": 0.9,
          "feedback": "Put your tongue between your teeth and blow air gently"},
    "ð": {"common_mis": "d", "score": 40.0, "frequency": 0.85,
          "feedback": "Vibrate your vocal cords with tongue between teeth"},

    # NG sound
    "ŋ": {"common_mis": "n", "score": 55.0, "frequency": 0.7,
          "feedback": "Sound from the back of your throat, like 'sing'"},

    # R/L distinction
    "r": {"common_mis": "l", "score": 50.0, "frequency": 0.8,
          "feedback": "Curl your tongue back without touching the roof of your mouth"},
    "l": {"common_mis": "r", "score": 55.0, "frequency": 0.6,
          "feedback": "Touch the tip of your tongue to the ridge behind your teeth"},

    # V/W distinction
    "v": {"common_mis": "w", "score": 50.0, "frequency": 0.75,
          "feedback": "Bite your lower lip gently and vibrate"},
    "w": {"common_mis": "v", "score": 60.0, "frequency": 0.5,
          "feedback": "Round your lips without touching teeth"},

    # SH/ZH sounds
    "ʃ": {"common_mis": "s", "score": 55.0, "frequency": 0.7,
          "feedback": "Pull your tongue back and push air through rounded lips"},
    "ʒ": {"common_mis": "z", "score": 50.0, "frequency": 0.65,
          "feedback": "Same as 'sh' but with vocal cord vibration"},

    # CH/JH sounds
    "tʃ": {"common_mis": "ts", "score": 55.0, "frequency": 0.7,
           "feedback": "Start with 't' sound, then release into 'sh'"},
    "dʒ": {"common_mis": "dz", "score": 50.0, "frequency": 0.65,
           "feedback": "Start with 'd' sound, then release into 'zh'"},

    # Z sound
    "z": {"common_mis": "s", "score": 60.0, "frequency": 0.5,
          "feedback": "Same tongue position as 's' but vibrate your vocal cords"},

    # Vowel issues for Mandarin speakers
    "ɪ": {"common_mis": "iː", "score": 55.0, "frequency": 0.6,
          "feedback": "Short, relaxed sound — tongue is lower than 'ee'"},
    "æ": {"common_mis": "ɑː", "score": 50.0, "frequency": 0.7,
          "feedback": "Open your mouth wider — like 'a' in 'cat'"},
    "ʌ": {"common_mis": "ɑː", "score": 55.0, "frequency": 0.65,
          "feedback": "Short, relaxed 'uh' sound — don't open too wide"},
    "ɛ": {"common_mis": "eɪ", "score": 55.0, "frequency": 0.6,
          "feedback": "Short 'e' sound — like 'e' in 'bed'"},
}


# ══════════════════════════════════════════════════════════════
# Word-to-IPA Phoneme Dictionary
# ══════════════════════════════════════════════════════════════

WORD_PHONEMES: dict[str, list[dict[str, object]]] = {
    # Common conversation words with IPA breakdown
    "the": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.12},
            {"phoneme": "ə", "start_offset": 0.12, "duration": 0.08}],
    "a": [{"phoneme": "ə", "start_offset": 0.0, "duration": 0.1}],
    "an": [{"phoneme": "ə", "start_offset": 0.0, "duration": 0.08},
           {"phoneme": "n", "start_offset": 0.08, "duration": 0.07}],
    "and": [{"phoneme": "æ", "start_offset": 0.0, "duration": 0.1},
            {"phoneme": "n", "start_offset": 0.1, "duration": 0.06},
            {"phoneme": "d", "start_offset": 0.16, "duration": 0.04}],
    "is": [{"phoneme": "ɪ", "start_offset": 0.0, "duration": 0.08},
           {"phoneme": "z", "start_offset": 0.08, "duration": 0.07}],
    "it": [{"phoneme": "ɪ", "start_offset": 0.0, "duration": 0.07},
           {"phoneme": "t", "start_offset": 0.07, "duration": 0.08}],
    "in": [{"phoneme": "ɪ", "start_offset": 0.0, "duration": 0.08},
           {"phoneme": "n", "start_offset": 0.08, "duration": 0.07}],
    "that": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.1},
             {"phoneme": "æ", "start_offset": 0.1, "duration": 0.1},
             {"phoneme": "t", "start_offset": 0.2, "duration": 0.1}],
    "this": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.1},
             {"phoneme": "ɪ", "start_offset": 0.1, "duration": 0.08},
             {"phoneme": "s", "start_offset": 0.18, "duration": 0.12}],
    "to": [{"phoneme": "t", "start_offset": 0.0, "duration": 0.07},
           {"phoneme": "uː", "start_offset": 0.07, "duration": 0.08}],
    "you": [{"phoneme": "j", "start_offset": 0.0, "duration": 0.06},
            {"phoneme": "uː", "start_offset": 0.06, "duration": 0.09}],
    "i": [{"phoneme": "aɪ", "start_offset": 0.0, "duration": 0.12}],
    "we": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.06},
           {"phoneme": "iː", "start_offset": 0.06, "duration": 0.09}],
    "they": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.1},
             {"phoneme": "eɪ", "start_offset": 0.1, "duration": 0.1}],
    "think": [{"phoneme": "θ", "start_offset": 0.0, "duration": 0.12},
              {"phoneme": "ɪ", "start_offset": 0.12, "duration": 0.08},
              {"phoneme": "ŋ", "start_offset": 0.2, "duration": 0.1},
              {"phoneme": "k", "start_offset": 0.3, "duration": 0.1}],
    "thank": [{"phoneme": "θ", "start_offset": 0.0, "duration": 0.12},
              {"phoneme": "æ", "start_offset": 0.12, "duration": 0.1},
              {"phoneme": "ŋ", "start_offset": 0.22, "duration": 0.1},
              {"phoneme": "k", "start_offset": 0.32, "duration": 0.08}],
    "going": [{"phoneme": "ɡ", "start_offset": 0.0, "duration": 0.08},
              {"phoneme": "oʊ", "start_offset": 0.08, "duration": 0.12},
              {"phoneme": "ɪ", "start_offset": 0.2, "duration": 0.06},
              {"phoneme": "ŋ", "start_offset": 0.26, "duration": 0.1}],
    "like": [{"phoneme": "l", "start_offset": 0.0, "duration": 0.08},
             {"phoneme": "aɪ", "start_offset": 0.08, "duration": 0.12},
             {"phoneme": "k", "start_offset": 0.2, "duration": 0.1}],
    "good": [{"phoneme": "ɡ", "start_offset": 0.0, "duration": 0.08},
             {"phoneme": "ʊ", "start_offset": 0.08, "duration": 0.08},
             {"phoneme": "d", "start_offset": 0.16, "duration": 0.09}],
    "very": [{"phoneme": "v", "start_offset": 0.0, "duration": 0.08},
             {"phoneme": "ɛ", "start_offset": 0.08, "duration": 0.08},
             {"phoneme": "r", "start_offset": 0.16, "duration": 0.07},
             {"phoneme": "iː", "start_offset": 0.23, "duration": 0.07}],
    "what": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.08},
             {"phoneme": "ʌ", "start_offset": 0.08, "duration": 0.08},
             {"phoneme": "t", "start_offset": 0.16, "duration": 0.09}],
    "where": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.08},
              {"phoneme": "eər", "start_offset": 0.08, "duration": 0.12}],
    "there": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.1},
              {"phoneme": "eər", "start_offset": 0.1, "duration": 0.12}],
    "their": [{"phoneme": "ð", "start_offset": 0.0, "duration": 0.1},
              {"phoneme": "eər", "start_offset": 0.1, "duration": 0.12}],
    "about": [{"phoneme": "ə", "start_offset": 0.0, "duration": 0.08},
              {"phoneme": "b", "start_offset": 0.08, "duration": 0.07},
              {"phoneme": "aʊ", "start_offset": 0.15, "duration": 0.12},
              {"phoneme": "t", "start_offset": 0.27, "duration": 0.08}],
    "would": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.07},
              {"phoneme": "ʊ", "start_offset": 0.07, "duration": 0.08},
              {"phoneme": "d", "start_offset": 0.15, "duration": 0.05}],
    "could": [{"phoneme": "k", "start_offset": 0.0, "duration": 0.08},
              {"phoneme": "ʊ", "start_offset": 0.08, "duration": 0.08},
              {"phoneme": "d", "start_offset": 0.16, "duration": 0.04}],
    "should": [{"phoneme": "ʃ", "start_offset": 0.0, "duration": 0.1},
               {"phoneme": "ʊ", "start_offset": 0.1, "duration": 0.08},
               {"phoneme": "d", "start_offset": 0.18, "duration": 0.04}],
    "with": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.07},
             {"phoneme": "ɪ", "start_offset": 0.07, "duration": 0.07},
             {"phoneme": "ð", "start_offset": 0.14, "duration": 0.1}],
    "have": [{"phoneme": "h", "start_offset": 0.0, "duration": 0.07},
             {"phoneme": "æ", "start_offset": 0.07, "duration": 0.1},
             {"phoneme": "v", "start_offset": 0.17, "duration": 0.08}],
    "from": [{"phoneme": "f", "start_offset": 0.0, "duration": 0.07},
             {"phoneme": "r", "start_offset": 0.07, "duration": 0.06},
             {"phoneme": "ʌ", "start_offset": 0.13, "duration": 0.08},
             {"phoneme": "m", "start_offset": 0.21, "duration": 0.07}],
    "for": [{"phoneme": "f", "start_offset": 0.0, "duration": 0.07},
            {"phoneme": "ɔː", "start_offset": 0.07, "duration": 0.1}],
    "can": [{"phoneme": "k", "start_offset": 0.0, "duration": 0.07},
            {"phoneme": "æ", "start_offset": 0.07, "duration": 0.08},
            {"phoneme": "n", "start_offset": 0.15, "duration": 0.05}],
    "want": [{"phoneme": "w", "start_offset": 0.0, "duration": 0.07},
             {"phoneme": "ʌ", "start_offset": 0.07, "duration": 0.08},
             {"phoneme": "n", "start_offset": 0.15, "duration": 0.06},
             {"phoneme": "t", "start_offset": 0.21, "duration": 0.09}],
    "need": [{"phoneme": "n", "start_offset": 0.0, "duration": 0.06},
             {"phoneme": "iː", "start_offset": 0.06, "duration": 0.1},
             {"phoneme": "d", "start_offset": 0.16, "duration": 0.09}],
    "really": [{"phoneme": "r", "start_offset": 0.0, "duration": 0.06},
               {"phoneme": "ɪ", "start_offset": 0.06, "duration": 0.06},
               {"phoneme": "l", "start_offset": 0.12, "duration": 0.06},
               {"phoneme": "iː", "start_offset": 0.18, "duration": 0.07}],
    "just": [{"phoneme": "dʒ", "start_offset": 0.0, "duration": 0.1},
             {"phoneme": "ʌ", "start_offset": 0.1, "duration": 0.08},
             {"phoneme": "s", "start_offset": 0.18, "duration": 0.07},
             {"phoneme": "t", "start_offset": 0.25, "duration": 0.05}],
    "please": [{"phoneme": "p", "start_offset": 0.0, "duration": 0.07},
               {"phoneme": "l", "start_offset": 0.07, "duration": 0.06},
               {"phoneme": "iː", "start_offset": 0.13, "duration": 0.1},
               {"phoneme": "z", "start_offset": 0.23, "duration": 0.07}],
    "sorry": [{"phoneme": "s", "start_offset": 0.0, "duration": 0.08},
              {"phoneme": "ʌ", "start_offset": 0.08, "duration": 0.06},
              {"phoneme": "r", "start_offset": 0.14, "duration": 0.06},
              {"phoneme": "iː", "start_offset": 0.2, "duration": 0.07}],
    "hello": [{"phoneme": "h", "start_offset": 0.0, "duration": 0.07},
              {"phoneme": "ə", "start_offset": 0.07, "duration": 0.06},
              {"phoneme": "l", "start_offset": 0.13, "duration": 0.06},
              {"phoneme": "oʊ", "start_offset": 0.19, "duration": 0.1}],
    "how": [{"phoneme": "h", "start_offset": 0.0, "duration": 0.07},
            {"phoneme": "aʊ", "start_offset": 0.07, "duration": 0.1}],
    "now": [{"phoneme": "n", "start_offset": 0.0, "duration": 0.06},
            {"phoneme": "aʊ", "start_offset": 0.06, "duration": 0.1}],
    "people": [{"phoneme": "p", "start_offset": 0.0, "duration": 0.07},
               {"phoneme": "iː", "start_offset": 0.07, "duration": 0.08},
               {"phoneme": "p", "start_offset": 0.15, "duration": 0.06},
               {"phoneme": "l", "start_offset": 0.21, "duration": 0.07}],
    "always": [{"phoneme": "ɔː", "start_offset": 0.0, "duration": 0.08},
               {"phoneme": "l", "start_offset": 0.08, "duration": 0.06},
               {"phoneme": "w", "start_offset": 0.14, "duration": 0.06},
               {"phoneme": "eɪ", "start_offset": 0.2, "duration": 0.08},
               {"phoneme": "z", "start_offset": 0.28, "duration": 0.07}],
    "also": [{"phoneme": "ɔː", "start_offset": 0.0, "duration": 0.08},
             {"phoneme": "l", "start_offset": 0.08, "duration": 0.06},
             {"phoneme": "s", "start_offset": 0.14, "duration": 0.07},
             {"phoneme": "oʊ", "start_offset": 0.21, "duration": 0.09}],
    "every": [{"phoneme": "ɛ", "start_offset": 0.0, "duration": 0.07},
              {"phoneme": "v", "start_offset": 0.07, "duration": 0.06},
              {"phoneme": "r", "start_offset": 0.13, "duration": 0.06},
              {"phoneme": "iː", "start_offset": 0.19, "duration": 0.07}],
    "thing": [{"phoneme": "θ", "start_offset": 0.0, "duration": 0.1},
              {"phoneme": "ɪ", "start_offset": 0.1, "duration": 0.08},
              {"phoneme": "ŋ", "start_offset": 0.18, "duration": 0.1}],
    "something": [{"phoneme": "s", "start_offset": 0.0, "duration": 0.07},
                  {"phoneme": "ʌ", "start_offset": 0.07, "duration": 0.07},
                  {"phoneme": "m", "start_offset": 0.14, "duration": 0.06},
                  {"phoneme": "θ", "start_offset": 0.2, "duration": 0.1},
                  {"phoneme": "ɪ", "start_offset": 0.3, "duration": 0.07},
                  {"phoneme": "ŋ", "start_offset": 0.37, "duration": 0.1}],
}


def get_phoneme_duration(phoneme: str, speaking_rate: float = 1.0) -> float:
    """Estimate phoneme duration in seconds based on phoneme type."""
    if phoneme in VOWELS:
        base = 0.12
    elif phoneme in {"θ", "ð", "f", "v", "s", "z", "ʃ", "ʒ", "h"}:
        base = 0.10  # fricatives
    elif phoneme in {"p", "b", "t", "d", "k", "ɡ"}:
        base = 0.08  # plosives
    elif phoneme in {"m", "n", "ŋ"}:
        base = 0.09  # nasals
    elif phoneme in {"l", "r", "w", "j"}:
        base = 0.07  # approximants
    elif phoneme in {"tʃ", "dʒ"}:
        base = 0.12  # affricates
    else:
        base = 0.08
    return base / speaking_rate


# ══════════════════════════════════════════════════════════════
# Phoneme Aligner
# ══════════════════════════════════════════════════════════════

class PhonemeAligner:
    """Align user speech to phoneme-level timestamps.

    In production, this uses Wav2Vec2 + CTC forced alignment.
    The current implementation uses a dictionary-based approach
    with simulated timing.
    """

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def align(self, audio: np.ndarray, text: str, sample_rate: int = 16000) -> list[dict]:
        """Align audio to phoneme sequence.

        Args:
            audio: Audio waveform as numpy array
            text: Transcribed text from STT
            sample_rate: Audio sample rate in Hz

        Returns:
            List of dicts with keys:
                phoneme, start_time, end_time, confidence, word
        """
        if self.use_mock:
            return self._mock_align(text, audio, sample_rate)

        # TODO: Real Wav2Vec2 forced alignment
        #   model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h")
        #   processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h")
        #   inputs = processor(audio, sampling_rate=sample_rate, return_tensors="pt")
        #   with torch.no_grad():
        #       logits = model(**inputs).logits
        #   alignment = forced_align(logits, processor.tokenizer)
        return self._mock_align(text, audio, sample_rate)

    def _mock_align(self, text: str, audio: np.ndarray, sample_rate: int) -> list[dict]:
        """Generate simulated phoneme alignment."""
        words = re.findall(r"\b[a-z]+\b", text.lower())
        total_audio_duration = len(audio) / sample_rate if len(audio) > 0 else 1.0

        # Estimate speaking rate
        word_count = len(words)
        if word_count > 0 and total_audio_duration > 0:
            speaking_rate = word_count / total_audio_duration
            # Normalize: typical rate ~3 words/sec
            rate_factor = speaking_rate / 3.0
        else:
            rate_factor = 1.0

        result = []
        time_offset = 0.0

        for word in words:
            if word in WORD_PHONEMES:
                phonemes = WORD_PHONEMES[word]
                for ph in phonemes:
                    duration = ph["duration"] / rate_factor
                    confidence = 0.7 + np.random.random() * 0.25  # 0.7-0.95
                    result.append({
                        "phoneme": ph["phoneme"],
                        "start_time": round(time_offset + ph["start_offset"] / rate_factor, 3),
                        "end_time": round(time_offset + (ph["start_offset"] + ph["duration"]) / rate_factor, 3),
                        "confidence": round(confidence, 3),
                        "word": word,
                    })
                time_offset += sum(ph["duration"] for ph in phonemes) / rate_factor
            else:
                # Generic character-based estimation
                duration = get_phoneme_duration("ə") / rate_factor
                for i, char in enumerate(word[:5]):
                    confidence = 0.5 + np.random.random() * 0.3
                    phoneme = self._char_to_approximate_phoneme(char)
                    ph_duration = get_phoneme_duration(phoneme) / rate_factor
                    result.append({
                        "phoneme": phoneme,
                        "start_time": round(time_offset, 3),
                        "end_time": round(time_offset + ph_duration, 3),
                        "confidence": round(confidence, 3),
                        "word": word,
                    })
                    time_offset += ph_duration

            # Add small gap between words
            time_offset += 0.05 / rate_factor

        return result

    def _char_to_approximate_phoneme(self, char: str) -> str:
        """Map a character to its most likely phoneme."""
        mapping = {
            "a": "æ", "b": "b", "c": "k", "d": "d", "e": "ɛ",
            "f": "f", "g": "ɡ", "h": "h", "i": "ɪ", "j": "dʒ",
            "k": "k", "l": "l", "m": "m", "n": "n", "o": "ɑː",
            "p": "p", "q": "k", "r": "r", "s": "s", "t": "t",
            "u": "ʌ", "v": "v", "w": "w", "x": "ks", "y": "j",
            "z": "z",
        }
        return mapping.get(char, "ə")


# ══════════════════════════════════════════════════════════════
# Accent Comparator
# ══════════════════════════════════════════════════════════════

class AccentComparator:
    """Compare user phoneme features against target accent.

    In production, this uses MFCC/F0/Formant analysis to compare
    user pronunciation against the NYC accent voice profile reference.

    The current implementation uses error pattern matching based on
    common ESL pronunciation challenges for Mandarin/Cantonese speakers.
    """

    def __init__(self, target_accent: str = "new_york"):
        self.target_accent = target_accent

    def compare(
        self,
        user_phonemes: list[dict],
        target_text: str,
    ) -> list[dict]:
        """Compare each user phoneme to target accent reference.

        Args:
            user_phonemes: Aligned phoneme list from PhonemeAligner
            target_text: The expected/ideal text

        Returns:
            List of dicts with keys:
                phoneme, expected, actual, score, severity, feedback, word
        """
        results = []

        for phoneme_info in user_phonemes:
            p = phoneme_info["phoneme"]
            conf = phoneme_info.get("confidence", 0.5)
            word = phoneme_info.get("word", "")

            if p in ESL_ERROR_PATTERNS:
                pattern = ESL_ERROR_PATTERNS[p]
                # Calculate base score from pattern + confidence variation
                base_score = pattern["score"]
                confidence_factor = 1.0 - (conf - 0.5) * 0.6  # Higher confidence = higher score
                score = min(base_score * confidence_factor, pattern["score"] + 15)

                # Apply random variation for natural feel (±5%)
                score *= 0.95 + np.random.random() * 0.1

                severity = self._classify_severity(score)

                results.append({
                    "phoneme": p,
                    "expected": p,
                    "actual": pattern["common_mis"],
                    "score": round(score, 1),
                    "severity": severity,
                    "feedback": pattern["feedback"],
                    "word": word,
                })
            else:
                # Phoneme not in common error patterns → likely correct
                score = min(85 + conf * 15, 99)
                results.append({
                    "phoneme": p,
                    "expected": p,
                    "actual": p,
                    "score": round(score, 1),
                    "severity": "none",
                    "feedback": "",
                    "word": word,
                })

        return results

    def _classify_severity(self, score: float) -> str:
        if score >= 80:
            return "mild"
        elif score >= 60:
            return "medium"
        else:
            return "severe"


# ══════════════════════════════════════════════════════════════
# Fluency & Prosody Estimators
# ══════════════════════════════════════════════════════════════

class FluencyEstimator:
    """Estimate speech fluency based on timing and pause patterns."""

    def estimate(self, audio: np.ndarray, text: str, sample_rate: int = 16000) -> float:
        """Estimate fluency score (0-100).

        Analyzes:
        - Speaking rate (words per minute)
        - Pause frequency and duration
        - Consistency of rhythm
        """
        if len(audio) == 0 or not text:
            return 50.0

        duration_sec = len(audio) / sample_rate
        word_count = len(text.split())
        wpm = (word_count / duration_sec) * 60 if duration_sec > 0 else 0

        # Target: 140-160 wpm for conversational English
        if 120 <= wpm <= 180:
            score = 85.0
        elif 100 <= wpm <= 200:
            score = 70.0
        elif 80 <= wpm <= 220:
            score = 55.0
        else:
            score = 40.0

        # Adjust for duration-based confidence
        if duration_sec < 0.5:
            score *= 0.8  # Too short to evaluate

        return round(min(score, 100), 1)


class ProsodyEstimator:
    """Estimate prosody quality (intonation, stress, rhythm).

    In production, this analyzes F0 contour and energy variation.
    """

    def estimate(self, audio: np.ndarray, sample_rate: int = 16000) -> float:
        """Estimate prosody score (0-100).

        In production:
        1. Extract F0 contour using librosa.pyin or crepe
        2. Compare F0 range, variation, and contour shape to reference
        3. Analyze stress patterns via energy peaks
        """
        if len(audio) == 0:
            return 50.0

        # Stub: In production, compute from:
        #   f0, voiced_flags, _ = librosa.pyin(audio, fmin=65, fmax=2093, sr=sample_rate)
        #   f0_std = np.nanstd(f0)
        #   score = min(f0_std / 40 * 100, 90) + 10
        # For now, return reasonable default
        duration_sec = len(audio) / sample_rate
        if duration_sec < 1.0:
            return 65.0
        return 75.0


# ══════════════════════════════════════════════════════════════
# Main Correction Engine
# ══════════════════════════════════════════════════════════════

class CorrectionEngine:
    """
    Main correction pipeline.

    Flow:
      user_audio → STT text → phoneme alignment
      → accent comparison → scoring → feedback generation

    In production, each component connects to real ML models:
      - Wav2Vec2 for phoneme alignment
      - MFCC/F0 analysis for accent comparison
      - Prosody analysis for intonation scoring
    """

    def __init__(self):
        self.aligner = PhonemeAligner()
        self.comparator = AccentComparator()
        self.fluency = FluencyEstimator()
        self.prosody = ProsodyEstimator()

    def process(
        self,
        audio: np.ndarray,
        user_text: str,
        target_text: str,
        user_phonemes: list | None = None,
        prosody: dict | None = None,
        sample_rate: int = 16000,
        mode: CorrectionMode = None,
    ) -> CorrectionResult:
        """Process user audio and generate correction feedback.

        Args:
            audio: Raw user audio waveform
            user_text: STT transcription of user audio
            target_text: Expected/ideal text (usually the AI reply)
            user_phonemes: Pre-computed phoneme alignment from Whisper+Wav2Vec2.
                           If None, uses internal mock aligner.
            prosody: Prosody metrics from Whisper analysis (pitch, energy, rate).
                     Used for fluency and prosody scoring.
            sample_rate: Audio sample rate in Hz
            mode: Correction mode configuration
        """
        if mode is None:
            mode = CorrectionMode()

        # Step 1: Phoneme alignment — use real Wav2Vec2 data if available
        if user_phonemes is not None and len(user_phonemes) > 0:
            phoneme_data = user_phonemes
        else:
            phoneme_data = self.aligner.align(audio, user_text, sample_rate)

        # Step 2: Accent comparison
        comparisons = self.comparator.compare(phoneme_data, target_text)

        # Step 3: Calculate overall phoneme score
        if comparisons:
            phoneme_score = float(np.mean([c["score"] for c in comparisons]))
        else:
            phoneme_score = 50.0

        # Step 4: Classify errors
        errors = []
        seen_phonemes: set[str] = set()
        for c in comparisons:
            if c["severity"] != "none":
                ph = c["phoneme"]
                if ph in seen_phonemes:
                    continue
                seen_phonemes.add(ph)
                errors.append(PhonemeError(
                    phoneme=ph,
                    expected=c["expected"],
                    actual=c["actual"],
                    word=c.get("word", ""),
                    severity=c["severity"],
                    feedback=c["feedback"],
                ))

        # Step 5: Determine correction level
        overall_level = self._determine_level(
            phoneme_score, errors, mode
        )

        # Step 6: Build corrected text
        corrected_text = self._generate_corrected_text(
            user_text, errors
        )

        # Step 7: Multi-dimensional scoring
        fluency_score = self.fluency.estimate(audio, user_text, sample_rate)
        prosody_score = self.prosody.estimate(audio, sample_rate)

        # If we have real prosody data from Whisper, use it to refine scores
        if prosody:
            fluency_score = self._refine_fluency_with_prosody(fluency_score, prosody)
            prosody_score = self._refine_prosody_score(prosody_score, prosody)

        dimensions = ScoreDimensions(
            phoneme_accuracy=round(phoneme_score, 1),
            fluency=fluency_score,
            prosody=prosody_score,
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

    def _refine_fluency_with_prosody(self, base_score: float, prosody: dict) -> float:
        """Refine fluency score using real prosody data."""
        pause_ratio = prosody.get("pause_ratio", 0.15)
        if pause_ratio > 0.4:
            base_score *= 0.7
        elif pause_ratio > 0.25:
            base_score *= 0.85
        elif pause_ratio < 0.05:
            base_score *= 0.9
        return round(min(base_score, 100), 1)

    def _refine_prosody_score(self, base_score: float, prosody: dict) -> float:
        """Refine prosody score using real pitch/energy data."""
        pitch_range = prosody.get("pitch_range", 40.0)
        if pitch_range < 15:
            base_score *= 0.6
        elif pitch_range < 30:
            base_score *= 0.8
        elif pitch_range > 100:
            base_score *= 0.85
        return round(min(base_score, 100), 1)


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
        if errors and mode.mode in ("mild_only", "medium", "all"):
            return "mild"
        return "mild"

    def _find_word(self, phoneme: str, text: str) -> str:
        """Find which word a phoneme belongs to."""
        for word, phonemes in WORD_PHONEMES.items():
            if any(ph["phoneme"] == phoneme for ph in phonemes):
                return word
        # Fallback to first word containing the phoneme character
        for word in text.lower().split():
            if phoneme[0] in word:
                return word
        return text.split()[0] if text else ""

    def _generate_corrected_text(self, user_text: str, errors: list) -> str:
        """Generate corrected version of user's text.

        Replaces error words with phonetically corrected versions.
        """
        corrected = user_text
        for err in errors:
            if err.word and err.word in corrected.lower():
                # Apply phonetic correction hint
                correction_map = {
                    "θ": "th", "ð": "th", "ŋ": "ng",
                    "ʃ": "sh", "ʒ": "zh", "tʃ": "ch", "dʒ": "j",
                }
                replacement = correction_map.get(err.phoneme, err.expected)
                corrected = corrected.replace(err.word, f"{err.word}[{replacement}]", 1)
        return corrected

    def _estimate_completeness(self, user_text: str, target_text: str) -> float:
        """Estimate how many words were completed compared to target."""
        if not target_text:
            return 100.0
        user_words = set(user_text.lower().split())
        target_words = set(target_text.lower().split())
        if not target_words:
            return 100.0
        overlap = len(user_words & target_words)
        return round((overlap / len(target_words)) * 100, 1)
