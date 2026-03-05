"""
Language-Concept Matrix Builder.

Integrates ASJP phoneme data, speaker counts, and language metadata into
a unified data structure ready for graph-based analysis.

This module bridges Wave 1 outputs (ASJP forms, speaker counts, phoneme normalization)
into a structured matrix of language-concept entries with enriched metadata.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from pangloss.data.asjp import ConceptData, LanguageData, load_asjp
from pangloss.data.phonemes import normalize_segments
from pangloss.data.speakers import get_speakers_for_asjp_language, load_speaker_counts


@dataclass
class MatrixEntry:
    """
    A single language form for a concept with enriched metadata.

    Attributes:
        language_id: ASJP language ID (e.g., "ENGLISH", "MANDARIN_BEIJING")
        phonemes: Normalized IPA phoneme list (tone/stress stripped, length preserved)
        speaker_count: Total speakers for this language (native + L2)
        language_family: Language family classification from ASJP
        language_name: Human-readable language name
        raw_value: Original transcription value from ASJP
    """

    language_id: str
    phonemes: List[str]
    speaker_count: int
    language_family: str
    language_name: str
    raw_value: str


@dataclass
class ConceptEntry:
    """
    Collection of language forms for a single concept with aggregate statistics.

    Attributes:
        concept_id: Concept ID from ASJP (e.g., "75")
        concept_name: Human-readable concept name (e.g., "*water")
        entries: List of MatrixEntry objects for this concept
        total_languages: Count of language forms
        total_speakers: Sum of speaker counts across all forms (raw, may inflate due to ASJP variants)
        language_families: Set of language families represented
        language_to_speakers: Maps language_id → speaker_count for each entry
        total_unique_speakers: De-duplicated speaker count (ISO-canonical, same ISO counted once)
    """

    concept_id: str
    concept_name: str
    entries: List[MatrixEntry]
    total_languages: int
    total_speakers: int
    language_families: set
    language_to_speakers: Dict[str, int]
    total_unique_speakers: int


def _serialize_matrix_entry(entry: MatrixEntry) -> dict:
    """Serialize MatrixEntry to JSON-compatible dict."""
    return {
        "language_id": entry.language_id,
        "phonemes": entry.phonemes,
        "speaker_count": entry.speaker_count,
        "language_family": entry.language_family,
        "language_name": entry.language_name,
        "raw_value": entry.raw_value,
    }


def _deserialize_matrix_entry(data: dict) -> MatrixEntry:
    """Deserialize dict to MatrixEntry dataclass."""
    return MatrixEntry(
        language_id=data["language_id"],
        phonemes=data["phonemes"],
        speaker_count=data["speaker_count"],
        language_family=data["language_family"],
        language_name=data["language_name"],
        raw_value=data["raw_value"],
    )


def _serialize_concept_entry(entry: ConceptEntry) -> dict:
    """Serialize ConceptEntry to JSON-compatible dict (sets → sorted lists)."""
    return {
        "concept_id": entry.concept_id,
        "concept_name": entry.concept_name,
        "entries": [_serialize_matrix_entry(e) for e in entry.entries],
        "total_languages": entry.total_languages,
        "total_speakers": entry.total_speakers,
        "language_families": sorted(list(entry.language_families)),
        "language_to_speakers": entry.language_to_speakers,
        "total_unique_speakers": entry.total_unique_speakers,
    }


def _deserialize_concept_entry(data: dict) -> ConceptEntry:
    """Deserialize dict to ConceptEntry dataclass (lists → sets)."""
    return ConceptEntry(
        concept_id=data["concept_id"],
        concept_name=data["concept_name"],
        entries=[_deserialize_matrix_entry(e) for e in data["entries"]],
        total_languages=data["total_languages"],
        total_speakers=data["total_speakers"],
        language_families=set(data["language_families"]),
        language_to_speakers=data["language_to_speakers"],
        total_unique_speakers=data["total_unique_speakers"],
    )


def _compute_cache_hash(data_dir: Path) -> dict:
    """
    Compute hash from file stats (mtime + size) for cache invalidation.

    Uses mtime + size (NOT full content) for 100MB+ files.

    Returns:
        Dict with file stats for forms.csv, parameters.csv, languages.csv, speakers.json
    """
    files = [
        data_dir / "cldf" / "forms.csv",
        data_dir / "cldf" / "parameters.csv",
        data_dir / "cldf" / "languages.csv",
        Path(__file__).parent.parent.parent / "data" / "speakers.json",
    ]

    meta = {"version": "2"}
    for file_path in files:
        if not file_path.exists():
            # Missing file invalidates cache
            return {}
        stat = os.stat(file_path)
        key_base = file_path.stem if file_path.stem != "speakers" else "speakers"
        meta[f"{key_base}_mtime"] = stat.st_mtime
        meta[f"{key_base}_size"] = stat.st_size

    return meta


def _load_matrix_cache(
    cache_path: Path, data_dir: Path
) -> Optional[Dict[str, ConceptEntry]]:
    """
    Load matrix from cache if valid (matching file stats).

    Args:
        cache_path: Path to cache JSON
        data_dir: ASJP data directory (for hash validation)

    Returns:
        Dict mapping concept_name to ConceptEntry, or None if cache invalid/missing
    """
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)

        # Validate cache structure
        if "meta" not in cached or "matrix" not in cached:
            print("Cache invalid: missing meta or matrix", file=sys.stderr)
            return None

        # Check if cache is stale (file stats changed)
        current_meta = _compute_cache_hash(data_dir)
        if not current_meta:
            print("Cache invalid: missing input files", file=sys.stderr)
            return None

        if cached["meta"] != current_meta:
            print("Cache invalidated: input files changed", file=sys.stderr)
            return None

        # Deserialize matrix
        matrix = {
            concept_name: _deserialize_concept_entry(data)
            for concept_name, data in cached["matrix"].items()
        }

        print(f"Cache hit: loaded {len(matrix)} concepts from cache", file=sys.stderr)
        return matrix

    except Exception as e:
        print(f"Warning: Could not load cache from {cache_path}: {e}", file=sys.stderr)
        return None


def _save_matrix_cache(
    matrix: Dict[str, ConceptEntry], cache_path: Path, data_dir: Path
):
    """
    Save matrix to cache with file stats metadata.

    Args:
        matrix: Dict mapping concept_name to ConceptEntry
        cache_path: Path to cache JSON
        data_dir: ASJP data directory (for hash computation)
    """
    try:
        meta = _compute_cache_hash(data_dir)
        if not meta:
            print(
                "Warning: Could not compute cache hash, skipping cache save",
                file=sys.stderr,
            )
            return

        cache_data = {
            "meta": meta,
            "matrix": {
                concept_name: _serialize_concept_entry(entry)
                for concept_name, entry in matrix.items()
            },
        }

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        print(f"Cache saved: {len(matrix)} concepts to {cache_path}", file=sys.stderr)

    except Exception as e:
        print(f"Warning: Could not save cache to {cache_path}: {e}", file=sys.stderr)


def build_matrix(
    asjp_data: Dict[str, ConceptData],
    speaker_counts: Dict[str, int],
    languages: Optional[Dict[str, LanguageData]] = None,
    no_cache: bool = False,
    cache_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Dict[str, ConceptEntry]:
    """
    Build language-concept matrix from ASJP data and speaker counts.

    Integrates:
    - ASJP forms (IPA segments) → normalized phonemes
    - Speaker counts → speaker_count per language
    - Language metadata → family, name

    Edge cases handled:
    - Languages without speaker counts: logged to stderr, use speaker_count=0
    - Empty segments after normalization: skip entry
    - Missing language metadata: use empty string for family/name

    Args:
        asjp_data: Dict mapping concept_id to ConceptData (from load_asjp)
        speaker_counts: Dict mapping language_id to speaker count (from load_speaker_counts)
        languages: Optional dict mapping language_id to LanguageData (default: load from ASJP)
        no_cache: If True, bypass cache and force rebuild
        cache_path: Path to cache JSON (default: data/matrix_cache.json)
        data_dir: ASJP data directory for cache validation (default: data/asjp)

    Returns:
        Dict mapping concept_name (e.g., "*water") to ConceptEntry with enriched data

    Example:
        >>> asjp_data = load_asjp('data/asjp')
        >>> speaker_counts = load_speaker_counts()
        >>> matrix = build_matrix(asjp_data, speaker_counts)
        >>> water = matrix['*water']
        >>> print(f"Languages: {water.total_languages}, Speakers: {water.total_speakers:,}")
    """
    # Set default paths
    if cache_path is None:
        cache_path = Path(__file__).parent.parent.parent / "data" / "matrix_cache.json"
    if data_dir is None:
        data_dir = Path("data/asjp")

    # Check cache (unless no_cache flag set)
    if not no_cache:
        cached_matrix = _load_matrix_cache(cache_path, data_dir)
        if cached_matrix is not None:
            return cached_matrix

    from pangloss.data.speakers import get_all_asjp_iso_mappings

    matrix = {}

    if languages is None:
        from pangloss.data.asjp import _parse_languages

        languages_file = Path("data/asjp/cldf/languages.csv")
        if languages_file.exists():
            languages = _parse_languages(languages_file)
        else:
            print(
                "Warning: languages.csv not found, using empty metadata",
                file=sys.stderr,
            )
            languages = {}

    asjp_to_iso = get_all_asjp_iso_mappings()
    from pangloss.data.speakers import load_asjp_languages

    iso_to_asjp_representative = load_asjp_languages()

    # Build ISO-canonical speaker count lookup
    # speaker_counts has mixed keys (ASJP ID or ISO code)
    # Normalize all keys to ISO codes for consistent lookup
    iso_speaker_counts = {}
    for key, count in speaker_counts.items():
        # If key is already an ISO code (lowercase 3-letter), use it directly
        if len(key) == 3 and key.islower():
            iso_speaker_counts[key] = count
        else:
            # Try to find ISO code for this ASJP ID
            # Reverse lookup: find which ISO maps to this ASJP ID
            found_iso = None
            for iso_code, asjp_id in iso_to_asjp_representative.items():
                if asjp_id == key:
                    found_iso = iso_code
                    break
            if found_iso:
                iso_speaker_counts[found_iso] = count
            else:
                # Keep original key as fallback
                iso_speaker_counts[key] = count

    unmapped_languages = set()

    for concept_id, concept in asjp_data.items():
        entries = []

        for form in concept.forms:
            normalized_phonemes = normalize_segments(form.ipa_segments)

            if not normalized_phonemes:
                continue

            # Look up speakers using ISO code
            iso_code = asjp_to_iso.get(form.language_id)
            if iso_code:
                speakers = iso_speaker_counts.get(iso_code, 0)
            else:
                speakers = 0

            if speakers == 0:
                unmapped_languages.add(form.language_id)

            lang_data = languages.get(form.language_id)
            if lang_data:
                language_family = lang_data.family or ""
                language_name = lang_data.name or form.language_id
            else:
                language_family = ""
                language_name = form.language_id

            entry = MatrixEntry(
                language_id=form.language_id,
                phonemes=normalized_phonemes,
                speaker_count=speakers,
                language_family=language_family,
                language_name=language_name,
                raw_value=form.raw_value,
            )

            entries.append(entry)

        total_languages = len(entries)
        total_speakers = sum(entry.speaker_count for entry in entries)
        language_families = set(
            entry.language_family for entry in entries if entry.language_family
        )

        # Build language_to_speakers mapping (per language_id, not deduplicated)
        language_to_speakers = {
            entry.language_id: entry.speaker_count for entry in entries
        }

        # Build ISO-canonical de-duplicated speaker count for reporting
        iso_speakers_seen = {}
        for entry in entries:
            iso_code = asjp_to_iso.get(entry.language_id)
            if iso_code and iso_code not in iso_speakers_seen:
                iso_speakers_seen[iso_code] = entry.speaker_count
            elif (
                not iso_code
                and entry.speaker_count > 0
                and entry.language_id not in iso_speakers_seen
            ):
                iso_speakers_seen[entry.language_id] = entry.speaker_count
        total_unique_speakers = sum(iso_speakers_seen.values())

        concept_entry = ConceptEntry(
            concept_id=concept_id,
            concept_name=concept.name,
            entries=entries,
            total_languages=total_languages,
            total_speakers=total_speakers,
            language_families=language_families,
            language_to_speakers=language_to_speakers,
            total_unique_speakers=total_unique_speakers,
        )

        matrix[concept.name] = concept_entry

    print(
        f"Matrix built: {len(matrix)} concepts, {len(unmapped_languages)} unmapped languages",
        file=sys.stderr,
    )

    # Save to cache (unless no_cache flag set)
    if not no_cache:
        _save_matrix_cache(matrix, cache_path, data_dir)

    return matrix


if __name__ == "__main__":
    # Test the module
    print("Loading ASJP data...", file=sys.stderr)
    asjp_data = load_asjp("data/asjp")

    print("Loading speaker counts...", file=sys.stderr)
    speaker_counts = load_speaker_counts()

    print("Building matrix...", file=sys.stderr)
    matrix = build_matrix(asjp_data, speaker_counts)

    # Show stats for water concept
    water = matrix.get("*water")
    if water:
        print("\n=== Water Concept Stats ===")
        print(f"Total languages: {water.total_languages}")
        print(f"Total speakers: {water.total_speakers:,}")
        print(f"Language families: {len(water.language_families)}")
        print(f"\nSample entries (first 5):")
        for entry in water.entries[:5]:
            phoneme_str = " ".join(entry.phonemes)
            print(
                f"  {entry.language_id}: /{phoneme_str}/ ({entry.speaker_count:,} speakers)"
            )
    else:
        print("Error: Water concept not found in matrix")
