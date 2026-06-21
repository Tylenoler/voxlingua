"""
Grapheme-to-Phoneme (g2p) converter for English.

Converts English text to IPA phoneme sequences using pronunciation rules
and a dictionary-based approach. Falls back to rule-based conversion
for words not in the dictionary.
"""

import re
from typing import Optional

# English vowel letters
VOWEL_LETTERS = set("aeiou")

# IPA phoneme inventory used by VoxLingua correction engine
IPA_VOWELS = {"iː", "ɪ", "eɪ", "ɛ", "æ", "ɑː", "ɒ", "ɔː", "oʊ", "ʊ", "uː",
              "ʌ", "ɜː", "ə", "aɪ", "aʊ", "ɔɪ", "ɪər", "eər", "ʊər"}
IPA_CONSONANTS = {"p", "b", "t", "d", "k", "ɡ", "f", "v", "θ", "ð", "s", "z",
                   "ʃ", "ʒ", "h", "m", "n", "ŋ", "l", "r", "w", "j", "tʃ", "dʒ"}

# Letter-to-phoneme mapping rules for English
# Format: (letter_pattern, IPA_phoneme, context)
LETTER_TO_IPA = {
    # Vowels
    "a": [("a_e", "eɪ"), ("ar", "ɑː"), ("ay", "eɪ"), ("ai", "eɪ"), ("au", "ɔː"),
          ("aw", "ɔː"), ("al", "ɔː"), ("a", "æ")],
    "e": [("ee", "iː"), ("ea", "iː"), ("er", "ɜː"), ("ey", "eɪ"), ("eu", "uː"),
          ("ew", "uː"), ("e", "ɛ")],
    "i": [("i_e", "aɪ"), ("ir", "ɜː"), ("igh", "aɪ"), ("i", "ɪ")],
    "o": [("o_e", "oʊ"), ("or", "ɔː"), ("oy", "ɔɪ"), ("oi", "ɔɪ"), ("oo", "uː"),
          ("ou", "aʊ"), ("ow", "aʊ"), ("oa", "oʊ"), ("o", "ɒ")],
    "u": [("u_e", "uː"), ("ur", "ɜː"), ("uy", "aɪ"), ("u", "ʌ")],
    # Consonants
    "c": [("ch", "tʃ"), ("ck", "k"), ("ci", "ʃ"), ("ce", "s"), ("c", "k")],
    "g": [("gh", "ɡ"), ("gi", "dʒ"), ("ge", "dʒ"), ("g", "ɡ")],
    "s": [("sh", "ʃ"), ("si", "ʒ"), ("ss", "s"), ("s", "s")],
    "t": [("th", "θ"), ("ti", "ʃ"), ("tch", "tʃ"), ("t", "t")],
    "x": [("x", "ks")],
    "q": [("qu", "kw")],
    "p": [("ph", "f"), ("p", "p")],
    "b": [("b", "b")],
    "d": [("d", "d"), ("dg", "dʒ")],
    "f": [("f", "f")],
    "h": [("h", "h")],
    "j": [("j", "dʒ")],
    "k": [("k", "k"), ("kn", "n")],
    "l": [("l", "l")],
    "m": [("m", "m")],
    "n": [("n", "n"), ("ng", "ŋ")],
    "r": [("r", "r")],
    "v": [("v", "v")],
    "w": [("w", "w"), ("wh", "w")],
    "y": [("y", "j")],
    "z": [("z", "z"), ("zh", "ʒ")],
}


def word_to_phonemes(word: str) -> list[str]:
    """Convert an English word to IPA phonemes using dictionary lookup or rules."""
    word_lower = word.lower().strip(".,!?;:'\"-()[]{}")

    if not word_lower:
        return []

    # Check dictionary first (imported from correction_engine)
    try:
        from core.correction_engine import WORD_PHONEMES
        if word_lower in WORD_PHONEMES:
            return [p["phoneme"] for p in WORD_PHONEMES[word_lower]]
    except ImportError:
        pass

    # Rule-based g2p conversion
    return _rule_based_g2p(word_lower)


def _rule_based_g2p(word: str) -> list[str]:
    """Simple rule-based grapheme-to-phoneme conversion."""
    phonemes = []
    i = 0
    word_len = len(word)

    while i < word_len:
        matched = False
        # Try multi-character patterns first (longest match)
        for length in range(4, 0, -1):
            if i + length > word_len:
                continue
            chunk = word[i:i + length]
            # Check if this chunk matches a known pattern
            first_letter = chunk[0]
            if first_letter in LETTER_TO_IPA:
                for pattern, ipa in LETTER_TO_IPA[first_letter]:
                    pattern_letter = pattern.replace("_", "")  # Handle a_e patterns
                    if chunk.lower() == pattern_letter:
                        phonemes.append(ipa)
                        i += length
                        matched = True
                        break
                if matched:
                    break

        if not matched:
            # Single letter mapping
            letter = word[i]
            if letter in VOWEL_LETTERS:
                phonemes.append({"a": "æ", "e": "ɛ", "i": "ɪ", "o": "ɒ", "u": "ʌ"}[letter])
            elif letter in "bcdfghjklmnpqrstvwxyz":
                consonant_map = {
                    "b": "b", "d": "d", "f": "f", "h": "h", "j": "dʒ",
                    "k": "k", "l": "l", "m": "m", "n": "n", "p": "p",
                    "r": "r", "s": "s", "t": "t", "v": "v", "w": "w",
                    "x": "ks", "y": "j", "z": "z", "c": "k", "g": "ɡ",
                    "q": "k",
                }
                phonemes.append(consonant_map.get(letter, letter))
            i += 1

    return phonemes


def text_to_phonemes(text: str) -> list[dict[str, object]]:
    """Convert full text to list of (word, phoneme) pairs with timing estimates."""
    result = []
    words = text.split()
    for word in words:
        phonemes = word_to_phonemes(word)
        if phonemes:
            result.append({
                "word": word.strip(".,!?;:'\""),
                "phonemes": phonemes,
            })
    return result
