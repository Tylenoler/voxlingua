"""
Wav2Vec2 Phoneme Aligner — forced alignment for pronunciation scoring.

Pipeline::

    user_audio + user_text
            │
            ▼
    ┌──────────────────┐
    │ torchaudio        │  frame-level acoustic features
    │ WAV2VEC2_ASR_BASE │  + CTC log-probabilities
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ CTC forced_align  │  character-level frame indices
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ CMUdict           │  map character boundaries
    │ pronunciation     │  → phoneme boundaries
    └────────┬─────────┘
             │
             ▼
    phoneme list with start/end timestamps + confidence
"""

import logging
import os
import re
import threading
import urllib.request
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("voxlingua.phoneme_aligner")

# ── ARPAbet ↔ IPA mapping ────────────────────────────────────────

ARPABET_TO_IPA: dict[str, str] = {
    # vowels — monophthongs
    "IY": "i",  "IH": "ɪ", "EY": "eɪ", "EH": "ɛ", "AE": "æ",
    "AA": "ɑ",  "AO": "ɔ", "OW": "oʊ", "UH": "ʊ", "UW": "u",
    "AH": "ʌ",  "ER": "ɝ", "AX": "ə",  "IX": "ɨ",
    # vowels — diphthongs
    "AY": "aɪ", "AW": "aʊ", "OY": "ɔɪ",
    # consonants — stops
    "P": "p",   "B": "b",   "T": "t",   "D": "d",
    "K": "k",   "G": "ɡ",
    # consonants — affricates
    "CH": "tʃ", "JH": "dʒ",
    # consonants — fricatives
    "F": "f",   "V": "v",   "TH": "θ",  "DH": "ð",
    "S": "s",   "Z": "z",   "SH": "ʃ",  "ZH": "ʒ",
    "HH": "h",
    # consonants — nasals
    "M": "m",   "N": "n",   "NG": "ŋ",
    # consonants — approximants
    "L": "l",   "R": "r",   "W": "w",   "Y": "j",
    "EL": "l̩", "EM": "m̩", "EN": "n̩",
}

# Phoneme confusability weights for scoring (0–1)
# Higher = harder to pronounce for ESL learners with L1 Chinese
PHONEME_DIFFICULTY: dict[str, float] = {
    "θ": 0.95, "ð": 0.95, "ŋ": 0.70, "r": 0.75,
    "l": 0.60, "ʃ": 0.55, "ʒ": 0.60, "tʃ": 0.50,
    "dʒ": 0.50, "æ": 0.55, "ʌ": 0.50, "ɝ": 0.65,
}

# ── default CMUdict URL ──────────────────────────────────────────

CMUDICT_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"

# Number of stress variants to keep per word
CMUDICT_CACHE = os.path.expanduser(
    os.path.join("~", ".cache", "voxlingua", "cmudict.dict")
)


# ── Torchaudio label set constants ───────────────────────────────

# From torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.get_labels()
WAV2VEC2_LABELS = [
    "<s>", "<pad>", "</s>", "<unk>", "|",
    "E", "T", "A", "O", "N", "I", "H", "S", "R", "D", "L",
    "U", "M", "W", "C", "F", "G", "Y", "P", "B", "V", "K",
    "'", "X", "J", "Q", "Z",
]
LABEL_TO_IDX: dict[str, int] = {lab: i for i, lab in enumerate(WAV2VEC2_LABELS)}
BLANK_ID = 0  # "<s>" is the CTC blank in torchaudio Wav2Vec2
UNK_ID = 3    # "<unk>"
SPACE_LABEL = "|"
SPACE_ID = 4


class Wav2Vec2Aligner:
    """Phoneme-level forced alignment using Wav2Vec2 + CTC + CMUdict.

    Usage::

        aligner = Wav2Vec2Aligner(device="cuda")
        aligner.load()
        phonemes = aligner.align(audio, "I think this is a good idea")
        # [{"phoneme": "ð", "start": 0.0, "end": 0.08, "confidence": 0.92},
        #  {"phoneme": "ɪ", "start": 0.08, "end": 0.15, "confidence": 0.88}, ...]
    """

    def __init__(self, device: str = "cuda"):
        self.device = self._resolve_device(device)
        self._model: Any = None
        self._pron_dict: dict[str, list[str]] = {}
        self._loaded = False
        self._lock = threading.Lock()
        self.sample_rate = 16000  # Wav2Vec2 expects 16 kHz mono

    # ── public API ────────────────────────────────────────────────

    def load(self) -> bool:
        """Load the Wav2Vec2 model and CMUdict. Returns True on success."""
        if self._loaded:
            return True

        with self._lock:
            if self._loaded:
                return True

            model_ok = self._load_model()
            dict_ok = self._load_cmudict()
            self._loaded = model_ok and dict_ok
            if self._loaded:
                logger.info(
                    "Phoneme aligner ready — %d words in CMUdict",
                    len(self._pron_dict),
                )
            return self._loaded

    def is_loaded(self) -> bool:
        return self._loaded

    def align(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int = 16000,
    ) -> list[dict]:
        """Align *audio* to the phonemes of *text*.

        Returns a list of phoneme dicts::

            {"phoneme": str, "start": float, "end": float, "confidence": float}
        """
        if not self._loaded:
            logger.warning("Aligner not loaded — returning empty phoneme list")
            return []

        if not text.strip():
            return []

        text_clean = self._clean_text(text)

        with self._lock:
            # 1. Character-level CTC alignment
            char_items = self._align_characters(audio, text_clean, sample_rate)
            if not char_items:
                return []

            # 2. Tokenise text to phonemes via CMUdict
            word_phonemes = self._text_to_phonemes(text_clean)

            # 3. Map character boundaries → phoneme boundaries
            return self._map_phonemes(char_items, word_phonemes)

    def unload(self) -> None:
        """Release GPU memory."""
        self._model = None
        self._loaded = False
        if self.device == "cuda":
            import torch
            torch.cuda.empty_cache()
        logger.info("Phoneme aligner unloaded")

    # ── character-level CTC alignment ─────────────────────────────

    def _align_characters(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int,
    ) -> list[dict]:
        """Run Wav2Vec2 + CTC forced alignment to get character timestamps.

        Returns list of ``{"char": str, "start": float, "end": float}``
        for each character in *text* (including spaces).
        """
        import torch
        import torchaudio
        import torchaudio.functional as aF

        # --- prepare audio ---
        if audio.ndim > 1:
            audio_np = audio.mean(axis=1)  # mono
        else:
            audio_np = audio

        # Resample to 16 kHz if needed
        if sample_rate != self.sample_rate:
            audio_t = torch.from_numpy(audio_np).float()
            audio_t = torchaudio.functional.resample(
                audio_t, sample_rate, self.sample_rate
            )
        else:
            audio_t = torch.from_numpy(audio_np).float()

        audio_t = audio_t.to(self.device)

        # --- run model ---
        with torch.no_grad():
            logits, _ = self._model(audio_t.unsqueeze(0))  # (1, T, C)
            emissions = logits.log_softmax(dim=-1)

        # --- convert text to token indices ---
        token_ids = self._text_to_token_ids(text.upper())
        if not token_ids:
            return []
        targets = torch.tensor([token_ids], device=self.device)

        # --- CTC forced alignment ---
        try:
            aligned = aF.forced_align(
                emissions,
                targets,
                blank=BLANK_ID,
                blank_is_beginning=True,
            )  # (1, N)
        except RuntimeError as exc:
            logger.error("CTC forced alignment failed: %s", exc)
            return []

        frame_indices = aligned[0].cpu().numpy()  # (N,)
        num_frames = emissions.shape[1]

        # --- convert frame indices to timestamps ---
        # Wav2Vec2 outputs one frame per ~20 ms of audio.
        # Use the model's time stride for accurate conversion.
        time_per_frame = self._time_per_frame(audio_t.shape[0], num_frames)

        char_items = []
        for i, frame_idx in enumerate(frame_indices):
            if frame_idx < 0 or frame_idx >= num_frames:
                continue
            start = max(0.0, (frame_idx - 0.5) * time_per_frame)
            end = min((frame_idx + 0.5) * time_per_frame, len(audio_np) / self.sample_rate)
            char_items.append({
                "char": WAV2VEC2_LABELS[token_ids[i]],
                "start": float(start),
                "end": float(end),
            })

        return char_items

    def _text_to_token_ids(self, text_upper: str) -> list[int]:
        """Convert uppercase text to Wav2Vec2 vocabulary indices."""
        ids: list[int] = []
        for ch in text_upper:
            if ch == " ":
                ids.append(SPACE_ID)
            elif ch in LABEL_TO_IDX:
                ids.append(LABEL_TO_IDX[ch])
            elif ch == "'":
                ids.append(LABEL_TO_IDX["'"])
            # else skip character (e.g. punctuation that got through)
        return ids

    @staticmethod
    def _time_per_frame(audio_len: int, num_frames: int) -> float:
        """Seconds per acoustic frame."""
        if num_frames <= 0:
            return 0.02
        return audio_len / (num_frames * 16000) if num_frames else 0.02

    # ── phoneme conversion ────────────────────────────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalise text: lowercase, strip punctuation except apostrophes."""
        text = text.lower().strip()
        # Keep letters, spaces, apostrophes
        text = re.sub(r"[^a-z' ]", "", text)
        # Collapse spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _text_to_phonemes(self, text: str) -> list[dict]:
        """Convert text to word-level phoneme sequences via CMUdict.

        Returns list of ``{"word": str, "phonemes": list[str]}``.
        """
        words = text.split()
        result = []
        for word in words:
            phonemes = self._lookup_phonemes(word)
            result.append({"word": word, "phonemes": phonemes})
        return result

    def _lookup_phonemes(self, word: str) -> list[str]:
        """Look up the phoneme sequence for *word* in CMUdict.

        Strips stress digits (0/1/2) from ARPAbet phonemes.
        Falls back to a naive letter-to-sound heuristic for OOV words.
        """
        word_upper = word.upper()
        if word_upper in self._pron_dict:
            raw = self._pron_dict[word_upper]
            # Strip stress digits (e.g. AH0 → AH)
            return [re.sub(r"\d", "", p) for p in raw]

        # Fallback: heuristic letter-to-phoneme
        logger.debug("OOV word '%s' — using heuristic phoneme guess", word)
        return self._heuristic_phonemes(word_upper)

    def _heuristic_phonemes(self, word: str) -> list[str]:
        """Naive letter-to-phoneme fallback for words not in CMUdict."""
        # Very simple: map each letter to a common phoneme
        letter_map = {
            "A": "AH", "B": "B", "C": "K", "D": "D", "E": "EH",
            "F": "F", "G": "G", "H": "HH", "I": "IH", "J": "JH",
            "K": "K", "L": "L", "M": "M", "N": "N", "O": "AA",
            "P": "P", "Q": "K", "R": "R", "S": "S", "T": "T",
            "U": "AH", "V": "V", "W": "W", "X": "KS", "Y": "Y",
            "Z": "Z",
        }
        phonemes: list[str] = []
        for ch in word:
            ph = letter_map.get(ch, "")
            if ph:
                if ph == "KS" and ch == "X":
                    phonemes.extend(["K", "S"])
                else:
                    phonemes.append(ph)
        return phonemes if phonemes else ["AA"]

    # ── character → phoneme mapping ───────────────────────────────

    @staticmethod
    def _map_phonemes(
        char_items: list[dict],
        word_phonemes: list[dict],
    ) -> list[dict]:
        """Map character-level timestamps to phoneme-level timestamps.

        For each word, divide its time span equally among its phonemes.
        """
        result: list[dict] = []
        word_idx = 0
        i = 0
        while i < len(char_items) and word_idx < len(word_phonemes):
            wp = word_phonemes[word_idx]
            word_phon_list = wp["phonemes"]
            if not word_phon_list:
                word_idx += 1
                continue

            # Find character span for this word (skip space characters)
            word_char_start = None
            word_char_end = None
            while i < len(char_items):
                ch = char_items[i]["char"]
                if ch == "|":  # space between words
                    i += 1
                    break
                if word_char_start is None:
                    word_char_start = char_items[i]["start"]
                word_char_end = char_items[i]["end"]
                i += 1

            if word_char_start is None or word_char_end is None:
                continue

            word_duration = word_char_end - word_char_start
            if word_duration <= 0 or not word_phon_list:
                continue

            # Divide the word time span equally among phonemes
            ph_duration = word_duration / len(word_phon_list)
            for j, arpabet in enumerate(word_phon_list):
                ipa = ARPABET_TO_IPA.get(arpabet, arpabet.lower())
                ph_start = word_char_start + j * ph_duration
                ph_end = ph_start + ph_duration
                # Confidence: use the average confidence of characters
                # in this phoneme's time range
                confidence = Wav2Vec2Aligner._estimate_confidence(
                    char_items, ph_start, ph_end
                )
                result.append({
                    "phoneme": ipa,
                    "start": round(ph_start, 3),
                    "end": round(ph_end, 3),
                    "confidence": round(confidence, 3),
                })

        return result

    @staticmethod
    def _estimate_confidence(
        char_items: list[dict],
        start: float,
        end: float,
    ) -> float:
        """Estimate phoneme confidence from the overlapping character
        alignment confidence.  Uses the proportion of time covered by
        non-blank characters as a proxy.
        """
        overlap = 0.0
        for ci in char_items:
            # Heuristic: each character's confidence is proportional to
            # the duration it covers (non-instantaneous = more confident)
            c_start = max(ci["start"], start)
            c_end = min(ci["end"], end)
            if c_end > c_start:
                overlap += c_end - c_start

        total = end - start
        if total <= 0:
            return 0.5
        raw = overlap / total
        # Scale: 0.5–0.95
        return 0.5 + raw * 0.45

    # ── model loading ─────────────────────────────────────────────

    def _load_model(self) -> bool:
        """Download and load the torchaudio Wav2Vec2 model."""
        try:
            import torchaudio

            logger.info("Loading Wav2Vec2 model (base, 960h) …")
            bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
            self._model = bundle.get_model().to(self.device)
            self._model.eval()
            logger.info("Wav2Vec2 model loaded on %s", self.device)
            return True
        except ImportError as exc:
            logger.error(
                "torchaudio not installed. Run: pip install torchaudio.  Error: %s",
                exc,
            )
            return False
        except Exception as exc:
            logger.error("Failed to load Wav2Vec2 model: %s", exc)
            return False

    # ── CMUdict loading ───────────────────────────────────────────

    def _load_cmudict(self) -> bool:
        """Download (if needed) and parse the CMU Pronouncing Dictionary."""
        if not self._download_cmudict():
            return False

        try:
            with open(CMUDICT_CACHE, encoding="latin-1") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";;;"):
                        continue
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    word = parts[0]
                    # Strip lexical stress markers (e.g. WORD(2))
                    word = re.sub(r"\(\d+\)$", "", word)
                    phonemes = parts[1:]
                    # Only keep the first pronunciation variant
                    if word not in self._pron_dict:
                        self._pron_dict[word] = phonemes
            logger.info(
                "CMUdict loaded: %d entries",
                len(self._pron_dict),
            )
            return True
        except Exception as exc:
            logger.error("Failed to parse CMUdict: %s", exc)
            return False

    def _download_cmudict(self) -> bool:
        """Download CMUdict from GitHub if not already cached."""
        os.makedirs(os.path.dirname(CMUDICT_CACHE), exist_ok=True)

        if os.path.isfile(CMUDICT_CACHE):
            logger.debug("CMUdict cached at %s", CMUDICT_CACHE)
            return True

        logger.info("Downloading CMUdict from %s …", CMUDICT_URL)
        try:
            urllib.request.urlretrieve(CMUDICT_URL, CMUDICT_CACHE)
            logger.info("CMUdict downloaded (%d KB)", os.path.getsize(CMUDICT_CACHE) // 1024)
            return True
        except Exception as exc:
            logger.error("Failed to download CMUdict: %s", exc)
            return False

    # ── misc ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device == "cuda":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    @staticmethod
    def arpabet_to_ipa(arpabet: str) -> str:
        """Convert a single ARPAbet phoneme to IPA."""
        return ARPABET_TO_IPA.get(arpabet, arpabet.lower())

    @staticmethod
    def phoneme_difficulty(ipa: str) -> float:
        """Return a phoneme's difficulty weight (0–1)."""
        return PHONEME_DIFFICULTY.get(ipa, 0.3)


# ── Module-level singleton ────────────────────────────────────────

_aligner: Optional[Wav2Vec2Aligner] = None


def get_aligner() -> Wav2Vec2Aligner:
    if _aligner is None:
        raise RuntimeError("Phoneme aligner not initialised")
    return _aligner


def set_aligner(aligner: Wav2Vec2Aligner) -> None:
    global _aligner
    _aligner = aligner


__all__ = [
    "Wav2Vec2Aligner",
    "get_aligner",
    "set_aligner",
    "ARPABET_TO_IPA",
]
