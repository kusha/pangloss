"""
Phoneme normalization pipeline for IPA consistency.

This module provides utilities for normalizing IPA (International Phonetic Alphabet)
transcriptions to ensure consistent matching and comparison across language data.

Normalization Strategy:
- Strip tone diacritics (e.g., á → a) for matching
- Strip stress marks (ˈ, ˌ)
- Preserve length markers (aː kept as-is for phonemic distinction)
- Apply Unicode NFC normalization (combining characters)
- Map IPA variant glyphs to canonical forms (g → ɡ)

Design Decision: Length markers (ː) are PRESERVED because vowel length is
phonemically distinctive in many languages. /aː/ and /a/ are different phonemes.
See: .sisyphus/notepads/pangloss-mvp/decisions.md
"""

import unicodedata
import re
from typing import List


# Tone diacritics (combining and precomposed)
# These include common pitch accent and tone marks
TONE_DIACRITICS = [
    "\u0300",  # grave accent (à)
    "\u0301",  # acute accent (á)
    "\u0302",  # circumflex (â)
    "\u0303",  # tilde (ã)
    "\u0304",  # macron (ā)
    "\u030c",  # caron (ǎ)
    "\u0331",  # macron below
    "\u0341",  # tone marks
    "\u0342",
    "\u0343",
    "\u0344",
]

# Stress marks (IPA primary and secondary stress)
STRESS_MARKS = ["ˈ", "ˌ"]

# IPA variant glyph mappings to canonical forms
# Key: variant glyph, Value: canonical IPA glyph
IPA_VARIANT_MAP = {
    "g": "ɡ",  # Latin g → IPA voiced velar stop (U+0261)
    ":": "ː",  # ASCII colon → IPA length marker (U+02D0)
}

# Articulatory feature groups for IPA phonemes
# Format: phoneme → (place, manner, voicing)
# Place: bilabial, labiodental, dental, alveolar, postalveolar, retroflex, palatal, velar, uvular, glottal
# Manner: stop, fricative, affricate, nasal, approximant, lateral, trill, tap, vowel
# Voicing: voiced, voiceless
ARTICULATORY_FEATURES = {
    # Stops
    "p": ("bilabial", "stop", "voiceless"),
    "b": ("bilabial", "stop", "voiced"),
    "t": ("alveolar", "stop", "voiceless"),
    "d": ("alveolar", "stop", "voiced"),
    "k": ("velar", "stop", "voiceless"),
    "ɡ": ("velar", "stop", "voiced"),
    "g": ("velar", "stop", "voiced"),  # Alias for ɡ
    "ʔ": ("glottal", "stop", "voiceless"),
    "q": ("uvular", "stop", "voiceless"),
    # Fricatives
    "f": ("labiodental", "fricative", "voiceless"),
    "v": ("labiodental", "fricative", "voiced"),
    "θ": ("dental", "fricative", "voiceless"),
    "ð": ("dental", "fricative", "voiced"),
    "s": ("alveolar", "fricative", "voiceless"),
    "z": ("alveolar", "fricative", "voiced"),
    "ʃ": ("postalveolar", "fricative", "voiceless"),
    "ʒ": ("postalveolar", "fricative", "voiced"),
    "ʂ": ("retroflex", "fricative", "voiceless"),
    "ʐ": ("retroflex", "fricative", "voiced"),
    "ç": ("palatal", "fricative", "voiceless"),
    "ʝ": ("palatal", "fricative", "voiced"),
    "x": ("velar", "fricative", "voiceless"),
    "ɣ": ("velar", "fricative", "voiced"),
    "χ": ("uvular", "fricative", "voiceless"),
    "ʁ": ("uvular", "fricative", "voiced"),
    "h": ("glottal", "fricative", "voiceless"),
    "ɦ": ("glottal", "fricative", "voiced"),
    # Affricates
    "tʃ": ("postalveolar", "affricate", "voiceless"),
    "dʒ": ("postalveolar", "affricate", "voiced"),
    "ts": ("alveolar", "affricate", "voiceless"),
    "dz": ("alveolar", "affricate", "voiced"),
    # Nasals
    "m": ("bilabial", "nasal", "voiced"),
    "n": ("alveolar", "nasal", "voiced"),
    "ɲ": ("palatal", "nasal", "voiced"),
    "ŋ": ("velar", "nasal", "voiced"),
    "ɳ": ("retroflex", "nasal", "voiced"),
    # Approximants
    "w": ("bilabial", "approximant", "voiced"),
    "ɹ": ("alveolar", "approximant", "voiced"),
    "j": ("palatal", "approximant", "voiced"),
    "ɰ": ("velar", "approximant", "voiced"),
    # Laterals
    "l": ("alveolar", "lateral", "voiced"),
    "ʎ": ("palatal", "lateral", "voiced"),
    "ɭ": ("retroflex", "lateral", "voiced"),
    # Trills and taps
    "r": ("alveolar", "trill", "voiced"),
    "ʀ": ("uvular", "trill", "voiced"),
    "ɾ": ("alveolar", "tap", "voiced"),
    "ɽ": ("retroflex", "tap", "voiced"),
    # Vowels - front
    "i": ("front", "vowel", "voiced"),
    "ɪ": ("front", "vowel", "voiced"),
    "e": ("front", "vowel", "voiced"),
    "ɛ": ("front", "vowel", "voiced"),
    "æ": ("front", "vowel", "voiced"),
    "y": ("front", "vowel", "voiced"),  # Front rounded vowel
    "ø": ("front", "vowel", "voiced"),
    "œ": ("front", "vowel", "voiced"),
    # Vowels - central
    "ə": ("central", "vowel", "voiced"),
    "ɘ": ("central", "vowel", "voiced"),
    "ɵ": ("central", "vowel", "voiced"),
    "ɜ": ("central", "vowel", "voiced"),
    "ɐ": ("central", "vowel", "voiced"),
    "ɨ": ("central", "vowel", "voiced"),
    "ʉ": ("central", "vowel", "voiced"),
    # Vowels - back
    "u": ("back", "vowel", "voiced"),
    "ʊ": ("back", "vowel", "voiced"),
    "o": ("back", "vowel", "voiced"),
    "ɔ": ("back", "vowel", "voiced"),
    "ɑ": ("back", "vowel", "voiced"),
    "ɒ": ("back", "vowel", "voiced"),
    "ʌ": ("back", "vowel", "voiced"),
    "ɤ": ("back", "vowel", "voiced"),
    # Vowels - open
    "a": ("central", "vowel", "voiced"),
}


def normalize_phoneme(phoneme: str) -> str:
    """
    Normalize a single phoneme for consistent matching.

    Applies the following transformations:
    1. Unicode NFC normalization (canonical composition)
    2. Strip tone diacritics
    3. Strip stress marks
    4. Map variant glyphs to canonical IPA forms

    Length markers (ː) are preserved as they represent phonemic distinctions.

    Args:
        phoneme: A single IPA phoneme (may be multiple Unicode characters)

    Returns:
        Normalized phoneme string (may be empty if only diacritics)

    Examples:
        >>> normalize_phoneme('á')
        'a'
        >>> normalize_phoneme('ˈa')
        'a'
        >>> normalize_phoneme('aː')
        'aː'
        >>> normalize_phoneme('g')
        'ɡ'
    """
    if not phoneme:
        return ""

    # Step 1: Apply Unicode NFC normalization
    # This combines base characters with combining diacritics
    normalized = unicodedata.normalize("NFC", phoneme)

    # Step 2: Strip stress marks (these are standalone characters)
    for stress_mark in STRESS_MARKS:
        normalized = normalized.replace(stress_mark, "")

    # Step 3: Strip tone diacritics
    # First, decompose to separate combining characters
    decomposed = unicodedata.normalize("NFD", normalized)

    # Remove tone diacritics
    result = []
    for char in decomposed:
        if char not in TONE_DIACRITICS:
            result.append(char)

    # Recompose to NFC
    normalized = unicodedata.normalize("NFC", "".join(result))

    # Step 4: Map variant glyphs to canonical forms
    for variant, canonical in IPA_VARIANT_MAP.items():
        normalized = normalized.replace(variant, canonical)

    return normalized


def normalize_segments(segments: List[str]) -> List[str]:
    """
    Normalize a list of phoneme segments.

    Applies phoneme normalization to each segment and filters out empty results
    (e.g., segments that contained only stress marks or tone diacritics).

    Args:
        segments: List of IPA phoneme segments

    Returns:
        List of normalized phoneme segments (empty segments filtered out)

    Examples:
        >>> normalize_segments(['ˈw', 'ɑː', 't', 'ə', 'ɹ'])
        ['w', 'ɑː', 't', 'ə', 'ɹ']
        >>> normalize_segments(['á', 'b', 'ˈ', 'c'])
        ['a', 'b', 'c']
    """
    normalized = [normalize_phoneme(seg) for seg in segments]
    # Filter out empty strings (segments that were only diacritics/stress marks)
    return [seg for seg in normalized if seg]


def segments_to_ipa_string(segments: List[str]) -> str:
    """
    Join phoneme segments into a readable IPA string.

    Segments are joined without delimiters (standard IPA transcription format).
    For phonemic transcription, wrap result in /.../ externally.
    For phonetic transcription, wrap result in [...] externally.

    Args:
        segments: List of IPA phoneme segments

    Returns:
        Joined IPA string

    Examples:
        >>> segments_to_ipa_string(['w', 'ɑː', 't', 'ə', 'ɹ'])
        'wɑːtəɹ'
        >>> segments_to_ipa_string(['h', 'ɛ', 'l', 'oʊ'])
        'hɛloʊ'
    """
    return "".join(segments)


def normalize_ipa_string(ipa_string: str, segment_pattern: str = r"[^\s]+") -> str:
    """
    Normalize an entire IPA string (convenience function).

    This function segments the IPA string by whitespace (or custom pattern),
    normalizes each segment, and rejoins them.

    Args:
        ipa_string: IPA transcription string (may include spaces between words)
        segment_pattern: Regex pattern to extract segments (default: non-whitespace)

    Returns:
        Normalized IPA string

    Examples:
        >>> normalize_ipa_string('ˈwɑːtəɹ')
        'wɑːtəɹ'
        >>> normalize_ipa_string('hɛˈloʊ wɜːrld')
        'hɛloʊ wɜːrld'
    """
    # Extract segments using pattern
    segments = re.findall(segment_pattern, ipa_string)

    # Normalize each segment as a unit
    normalized_segments = []
    for segment in segments:
        # Treat each space-separated token as a unit to normalize
        # Split into individual phonemes if needed (here we normalize the whole token)
        normalized = normalize_phoneme(segment)
        if normalized:
            normalized_segments.append(normalized)

    # Preserve original spacing structure
    # For now, join with spaces if original had spaces
    if " " in ipa_string:
        return " ".join(normalized_segments)
    else:
        return "".join(normalized_segments)


def phoneme_distance(p1: str, p2: str) -> float:
    """
    Calculate articulatory distance between two phonemes.

    Returns a value between 0.0 (identical) and 1.0 (completely different).
    Distance is based on articulatory features: place, manner, and voicing.

    Distance scale:
    - 0.0: Identical phonemes
    - 0.1: Same manner and place, voicing differs (e.g., /t/ vs /d/)
    - 0.3: Same manner, different place (e.g., /t/ vs /k/)
    - 0.5: Same manner, both place and voicing differ
    - 0.7: Different manner within consonants (e.g., /t/ vs /s/)
    - 1.0: Vowel vs consonant, or unknown phoneme

    Multi-character phonemes (tʃ, dʒ, aː) are looked up directly first,
    then fall back to base character (first character) if not found.

    Args:
        p1: First IPA phoneme
        p2: Second IPA phoneme

    Returns:
        Distance value between 0.0 and 1.0

    Examples:
        >>> phoneme_distance('t', 't')
        0.0
        >>> phoneme_distance('t', 'd')  # Voicing difference
        0.1
        >>> phoneme_distance('t', 'k')  # Place difference
        0.3
        >>> phoneme_distance('a', 't')  # Vowel vs consonant
        1.0
    """
    if p1 == p2:
        return 0.0

    def get_features(phoneme: str):
        if phoneme in ARTICULATORY_FEATURES:
            return ARTICULATORY_FEATURES[phoneme]
        if len(phoneme) > 1 and phoneme[0] in ARTICULATORY_FEATURES:
            return ARTICULATORY_FEATURES[phoneme[0]]
        return None

    f1 = get_features(p1)
    f2 = get_features(p2)

    if f1 is None or f2 is None:
        return 1.0

    place1, manner1, voicing1 = f1
    place2, manner2, voicing2 = f2

    if manner1 == "vowel" and manner2 != "vowel":
        return 1.0
    if manner1 != "vowel" and manner2 == "vowel":
        return 1.0

    if manner1 != manner2:
        return 0.7

    place_differs = place1 != place2
    voicing_differs = voicing1 != voicing2

    if not place_differs and not voicing_differs:
        return 0.0
    elif not place_differs and voicing_differs:
        return 0.1
    elif place_differs and not voicing_differs:
        return 0.3
    else:
        return 0.5


def fuzzy_phoneme_match(p1: str, p2: str, threshold: float = 0.5) -> bool:
    """
    Check if two phonemes match within a fuzzy threshold.

    Convenience function for phoneme_distance. Returns True if the
    articulatory distance is less than the threshold.

    Args:
        p1: First IPA phoneme
        p2: Second IPA phoneme
        threshold: Maximum distance for a match (default: 0.5)

    Returns:
        True if distance < threshold, False otherwise

    Examples:
        >>> fuzzy_phoneme_match('t', 'd')  # Voicing difference (0.1 < 0.5)
        True
        >>> fuzzy_phoneme_match('t', 'k')  # Place difference (0.3 < 0.5)
        True
        >>> fuzzy_phoneme_match('a', 't')  # Vowel vs consonant (1.0 >= 0.5)
        False
    """
    return phoneme_distance(p1, p2) < threshold
