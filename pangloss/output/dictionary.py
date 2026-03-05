"""
Dictionary Output Formatter.

Formats pipeline results into structured JSON/YAML dictionary files
for the Pangloss language synthesis system.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from pangloss.algo.generator import SyntheticWord
from pangloss.algo.collisions import detect_collisions


def format_dictionary(
    results: Dict[str, List[SyntheticWord]],
    matrix_entries: Optional[Dict[str, List[Any]]] = None,
    concept_totals: Optional[Dict[str, int]] = None,
    asjp_to_iso: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Format pipeline results into structured dictionary.

    Args:
        results: Map of concept_name → list of selected SyntheticWords
        matrix_entries: Map of concept_name → list of MatrixEntry objects (for speaker counts)
        concept_totals: Map of concept_name → total_unique_speakers (for coverage calculation)
        asjp_to_iso: Map of ASJP language_id → ISO 639-3 code (for deduplication)

    Returns:
        Dictionary with concepts list and metadata
        matrix_entries: Optional map of concept_name → list of MatrixEntry objects
            Used to extract language family information for covered languages

    Returns:
        Dictionary with structure:
        {
          "concepts": [
            {
              "concept": "water",
              "synonyms": [
                {
                  "form": "shuei",
                  "ipa": "/ʃuei/",
                  "covers": ["YUE_GUANGZHOU_1", ...],
                  "speaker_count": 62900000,
                  "coverage_pct": 27.5,
                  "source_pattern": "Cluster /ʃ-u-e-i/",
                  "reasoning": "Full reasoning trail..."
                }
              ],
              "total_coverage": 77.2,
              "total_speakers": 176800000,
              "language_families_covered": ["Sino-Tibetan", ...],
              "synonym_count": 20
            }
          ]
        }
    """
    concepts = []

    for concept_name, synonyms in results.items():
        formatted_synonyms = []
        for word in synonyms:
            formatted_synonyms.append(
                {
                    "form": word.form,
                    "ipa": word.ipa,
                    "covers": sorted(list(word.covered_languages)),
                    "speaker_count": word.speaker_count,
                    "coverage_pct": round(word.coverage_pct, 2),
                    "source_pattern": _generate_source_pattern(word),
                    "reasoning": word.reasoning,
                }
            )

        all_languages = set()
        for word in synonyms:
            all_languages.update(word.covered_languages)

        lang_speaker_counts = {}
        if matrix_entries and concept_name in matrix_entries:
            for entry in matrix_entries[concept_name]:
                lang_speaker_counts[entry.language_id] = entry.speaker_count

        # Deduplicate speaker counts by ISO code when summing
        total_speakers = 0
        if asjp_to_iso:
            iso_speakers_seen = {}
            for lang_id in all_languages:
                if lang_id in lang_speaker_counts:
                    iso = asjp_to_iso.get(lang_id, lang_id)
                    if iso not in iso_speakers_seen:
                        iso_speakers_seen[iso] = lang_speaker_counts[lang_id]
            total_speakers = sum(iso_speakers_seen.values())
        else:
            for lang_id in all_languages:
                if lang_id in lang_speaker_counts:
                    total_speakers += lang_speaker_counts[lang_id]

        language_families = _extract_families_from_synonyms(
            synonyms, concept_name, matrix_entries
        )

        concept_total_speakers = (
            concept_totals.get(concept_name, sum(lang_speaker_counts.values()))
            if concept_totals
            else (
                sum(lang_speaker_counts.values())
                if lang_speaker_counts
                else total_speakers
            )
        )
        total_coverage = (
            (total_speakers / concept_total_speakers * 100)
            if concept_total_speakers > 0
            else 0.0
        )

        concepts.append(
            {
                "concept": concept_name,
                "synonyms": formatted_synonyms,
                "total_coverage": round(total_coverage, 2),
                "total_speakers": total_speakers,
                "language_families_covered": sorted(list(language_families)),
                "synonym_count": len(synonyms),
            }
        )

    # Add collision report
    collisions = detect_collisions(results)

    return {"concepts": concepts, "collisions": collisions}


def _generate_source_pattern(word: SyntheticWord) -> str:
    """
    Generate human-readable source pattern description.

    For MVP, uses phoneme-based cluster description.
    Future: Could extract family info from covered_languages.

    Args:
        word: SyntheticWord with phonemes and IPA

    Returns:
        Pattern string like "Cluster /ʃ-u-e-i/"
    """
    phoneme_cluster = "-".join(word.phonemes[:4])
    if len(word.phonemes) > 4:
        phoneme_cluster += "-..."

    return f"Cluster /{phoneme_cluster}/"


def _extract_families_from_synonyms(
    synonyms: List[SyntheticWord],
    concept_name: str,
    matrix_entries: Optional[Dict[str, List[Any]]] = None,
) -> Set[str]:
    """
    Extract language family names from covered languages.

    If matrix_entries provided, looks up family info from MatrixEntry objects.
    Otherwise falls back to heuristic extraction from reasoning text.

    Args:
        synonyms: List of SyntheticWords
        concept_name: Concept name to look up in matrix_entries
        matrix_entries: Optional map of concept_name → list of MatrixEntry

    Returns:
        Set of detected family names
    """
    families = set()

    if matrix_entries and concept_name in matrix_entries:
        lang_to_family = {
            entry.language_id: entry.language_family
            for entry in matrix_entries[concept_name]
            if entry.language_family
        }

        for word in synonyms:
            for lang_id in word.covered_languages:
                if lang_id in lang_to_family:
                    family = lang_to_family[lang_id]
                    if family:
                        families.add(family)
    else:
        family_keywords = [
            "Sino-Tibetan",
            "Indo-European",
            "Afro-Asiatic",
            "Niger-Congo",
            "Austronesian",
            "Trans-New Guinea",
            "Turkic",
            "Uralic",
            "Dravidian",
            "Japonic",
            "Koreanic",
            "Atlantic-Congo",
            "Austroasiatic",
            "Tai-Kadai",
            "Nilo-Saharan",
            "Khoisan",
            "Germanic",
            "Romance",
            "Slavic",
            "Sinitic",
            "Indo-Aryan",
        ]

        for word in synonyms:
            reasoning_text = word.reasoning
            for family in family_keywords:
                if family in reasoning_text:
                    families.add(family)

    return families


def save_dictionary(dictionary: dict, path: str, format: str = "json") -> None:
    """
    Save dictionary to file in JSON or YAML format.

    Args:
        dictionary: Formatted dictionary from format_dictionary()
        path: Output file path
        format: "json" or "yaml"

    Raises:
        ValueError: If format is invalid or YAML requested but not available
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dictionary, f, indent=2, ensure_ascii=False)
    elif format == "yaml":
        if not YAML_AVAILABLE:
            raise ValueError("YAML format requested but PyYAML not installed")
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(dictionary, f, allow_unicode=True, sort_keys=False)  # type: ignore[name-defined]
    else:
        raise ValueError(f"Invalid format: {format}. Must be 'json' or 'yaml'")


def format_summary(dictionary: dict) -> dict:
    """
    Generate aggregate statistics summary from dictionary.

    Args:
        dictionary: Formatted dictionary with concepts list

    Returns:
        Summary statistics:
        {
          "total_concepts": 40,
          "avg_coverage_pct": 75.3,
          "min_coverage_pct": 45.2,
          "max_coverage_pct": 92.1,
          "avg_synonym_count": 3.2,
          "min_synonym_count": 1,
          "max_synonym_count": 20,
          "total_unique_languages": 8524,
          "total_unique_families": 387
        }
    """
    concepts = dictionary.get("concepts", [])

    if not concepts:
        return {
            "total_concepts": 0,
            "avg_coverage_pct": 0.0,
            "min_coverage_pct": 0.0,
            "max_coverage_pct": 0.0,
            "avg_synonym_count": 0.0,
            "min_synonym_count": 0,
            "max_synonym_count": 0,
            "total_unique_languages": 0,
            "total_unique_families": 0,
        }

    coverages = [c["total_coverage"] for c in concepts]
    synonym_counts = [c["synonym_count"] for c in concepts]

    all_languages = set()
    all_families = set()
    for concept in concepts:
        for synonym in concept["synonyms"]:
            all_languages.update(synonym["covers"])
        all_families.update(concept["language_families_covered"])

    return {
        "total_concepts": len(concepts),
        "avg_coverage_pct": round(sum(coverages) / len(coverages), 2),
        "min_coverage_pct": round(min(coverages), 2),
        "max_coverage_pct": round(max(coverages), 2),
        "avg_synonym_count": round(sum(synonym_counts) / len(synonym_counts), 2),
        "min_synonym_count": min(synonym_counts),
        "max_synonym_count": max(synonym_counts),
        "total_unique_languages": len(all_languages),
        "total_unique_families": len(all_families),
    }
