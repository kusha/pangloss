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
