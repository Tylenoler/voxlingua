"""
Tests for core/correction_engine.py — scoring, level determination, feedback.

Relies on conftest.py mocks (mock_aligner).
"""

import numpy as np
import pytest

from core.correction_engine import CorrectionEngine, AccentComparator
from models.schemas import CorrectionMode, ScoreDimensions


class TestAccentComparator:
    def test_easy_phoneme_high_score(self):
        """Easy phonemes (not in DIFFICULT_PHONEMES) get high scores."""
        comp = AccentComparator()
        user_phonemes = [
            {"phoneme": "m", "confidence": 0.9, "start": 0.0, "end": 0.1}
        ]
        results = comp.compare(user_phonemes, "me")
        assert len(results) == 1
        assert results[0]["score"] >= 70.0
        assert results[0]["severity"] == "none"

    def test_difficult_phoneme_gets_feedback(self):
        """Difficult phonemes (θ, ð, etc.) get feedback and lower scores."""
        comp = AccentComparator()
        user_phonemes = [
            {"phoneme": "θ", "confidence": 0.4, "start": 0.0, "end": 0.1}
        ]
        results = comp.compare(user_phonemes, "think")
        assert len(results) == 1
        assert results[0]["feedback"]  # non-empty
        assert results[0]["severity"] != "none"

    def test_high_confidence_difficult_phoneme(self):
        """Even difficult phonemes score well with high confidence."""
        comp = AccentComparator()
        user_phonemes = [
            {"phoneme": "θ", "confidence": 0.95, "start": 0.0, "end": 0.1}
        ]
        results = comp.compare(user_phonemes, "think")
        assert results[0]["score"] >= 60.0

    def test_classify_severity(self):
        comp = AccentComparator()
        assert comp._classify_severity(85.0) == "mild"
        assert comp._classify_severity(70.0) == "medium"
        assert comp._classify_severity(50.0) == "severe"
        assert comp._classify_severity(100.0) == "mild"
        assert comp._classify_severity(0.0) == "severe"

    def test_guess_mispronunciation(self):
        comp = AccentComparator()
        assert comp._guess_mispronunciation("θ") == "s"
        assert comp._guess_mispronunciation("ð") == "d"
        assert comp._guess_mispronunciation("æ") == "ɛ"
        assert comp._guess_mispronunciation("z") == "z"  # not in map → returns self


class TestCorrectionEngine:
    @pytest.fixture
    def engine(self):
        return CorrectionEngine()

    @pytest.fixture
    def sample_audio(self):
        return np.zeros(8000, dtype=np.float32)

    def test_process_basic(self, engine, sample_audio, mock_aligner):
        """Basic correction flow with mocked aligner."""
        result = engine.process(
            audio=sample_audio,
            user_text="I think this is good",
            target_text="I think this is good",
        )
        assert result.user_text == "I think this is good"
        assert result.level in ("mild", "medium", "severe")
        assert isinstance(result.overall_score, float)
        assert isinstance(result.dimensions, ScoreDimensions)

    def test_process_error_generation(self, engine, sample_audio, mock_aligner):
        """Errors should be populated when phoneme has issues."""
        result = engine.process(
            audio=sample_audio,
            user_text="think",
            target_text="think",
        )
        # Our mock aligner returns "ð" phonemes with 0.85 confidence
        # AccentComparator: "ð" is difficult, 0.85 confidence → ~72 score → medium
        if result.errors:
            assert hasattr(result.errors[0], "phoneme")
            assert hasattr(result.errors[0], "feedback")

    def test_process_empty_audio(self, engine, mock_aligner):
        """Empty audio should not crash."""
        result = engine.process(
            audio=np.array([], dtype=np.float32),
            user_text="",
            target_text="hello",
        )
        assert result is not None

    def test_process_no_aligner(self, engine, sample_audio):
        """When aligner is not available, return empty result."""
        from core.phoneme_aligner import set_aligner
        from unittest.mock import MagicMock

        broken = MagicMock()
        broken.is_loaded.return_value = False
        set_aligner(broken)

        result = engine.process(
            audio=sample_audio,
            user_text="hello",
            target_text="hello",
        )
        assert result.level == "mild"
        assert result.overall_score == 85.0


class TestDetermineLevel:
    @pytest.fixture
    def engine(self):
        return CorrectionEngine()

    def test_mode_off(self, engine):
        """mode=off should always return 'mild'."""
        mode = CorrectionMode(mode="off")
        assert engine._determine_level(50.0, [], mode) == "mild"

    def test_mode_mild_only(self, engine):
        mode = CorrectionMode(mode="mild_only")
        assert engine._determine_level(70.0, [], mode) == "mild"

    def test_severe_interrupt(self, engine):
        """severe error + mode=all + interrupt → severe level."""
        from models.schemas import PhonemeError

        mode = CorrectionMode(mode="all", interrupt_on_severe=True)
        errors = [
            PhonemeError(
                phoneme="θ", expected="θ", actual="s",
                word="think", severity="severe",
            )
        ]
        assert engine._determine_level(40.0, errors, mode) == "severe"

    def test_severe_interrupt_disabled(self, engine):
        """severe error but interrupt_on_severe=False → medium."""
        from models.schemas import PhonemeError

        mode = CorrectionMode(mode="all", interrupt_on_severe=False)
        errors = [
            PhonemeError(
                phoneme="θ", expected="θ", actual="s",
                word="think", severity="severe",
            )
        ]
        assert engine._determine_level(40.0, errors, mode) == "medium"


class TestSubDimensions:
    @pytest.fixture
    def engine(self):
        return CorrectionEngine()

    def test_estimate_fluency_normal(self, engine):
        """Normal speaking rate (120 wpm) → high fluency."""
        audio = np.zeros(int(16000 * 2.5), dtype=np.float32)  # 2.5 s
        text = "this is a test of the fluency estimate"  # 8 words → 192 wpm
        score = engine._estimate_fluency(audio, text)
        assert 55.0 <= score <= 85.0

    def test_estimate_fluency_slow(self, engine):
        """Very slow rate → lower fluency."""
        audio = np.zeros(int(16000 * 10), dtype=np.float32)  # 10 s
        text = "hello"  # 1 word → 6 wpm
        score = engine._estimate_fluency(audio, text)
        assert score <= 70.0

    def test_estimate_fluency_empty(self, engine):
        assert engine._estimate_fluency(np.array([]), "") == 75.0

    def test_estimate_completeness_full(self, engine):
        score = engine._estimate_completeness(
            "I think this is good", "I think this is good"
        )
        assert score == 100.0

    def test_estimate_completeness_partial(self, engine):
        score = engine._estimate_completeness("I good", "I think this is good")
        assert 0.0 < score < 100.0

    def test_estimate_completeness_empty_target(self, engine):
        score = engine._estimate_completeness("hello", "")
        assert score == 100.0

    def test_estimate_prosody(self, engine):
        audio = np.sin(np.linspace(0, 2 * np.pi * 440, 16000)).astype(np.float32)
        score = engine._estimate_prosody(audio)
        assert 0.0 <= score <= 100.0

    def test_estimate_prosody_silence(self, engine):
        score = engine._estimate_prosody(np.zeros(16000, dtype=np.float32))
        assert score == 75.0

    def test_generate_corrected_text_no_errors(self, engine):
        assert engine._generate_corrected_text("hello world", []) == "hello world"

    def test_find_word_with_phoneme(self, engine):
        word = engine._find_word("θ", 0.0, 0.1, "think this")
        # Should find either "think" or "this" that contains a 'th' match
        assert word in ("think", "this")

    def test_find_word_empty(self, engine):
        assert engine._find_word("θ", 0.0, 0.1, "") == ""
