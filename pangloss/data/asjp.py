"""
ASJP (Automated Similarity Judgment Program) dataset parser.

Parses CLDF-formatted ASJP v21 data to extract 40 core Swadesh concepts
with IPA phoneme segments for cross-linguistic analysis.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FormData:
    """A single word form for a concept in a language."""

    language_id: str
    concept_id: str
    raw_value: str
    ipa_segments: List[str]  # Space-separated phonemes


@dataclass
class LanguageData:
    """Metadata for a language in ASJP."""

    language_id: str
    name: str
    family: str
    iso_code: Optional[str]
    coordinates: Optional[tuple[float, float]]  # (latitude, longitude)


@dataclass
class ConceptData:
    """A core Swadesh concept with forms across languages."""

    concept_id: str
    name: str  # e.g., "*water", "*fire"
    forms: List[FormData]


def load_asjp(data_dir: str) -> Dict[str, ConceptData]:
    """
    Load ASJP dataset and return 40 core Swadesh concepts.

    Args:
        data_dir: Path to ASJP data directory (e.g., 'data/asjp')

    Returns:
        Dict mapping concept_id to ConceptData for 40 core concepts

    Raises:
        FileNotFoundError: If CLDF files are missing
        ValueError: If data structure is invalid
    """
    data_path = Path(data_dir)
    cldf_path = data_path / "cldf"

    # Verify paths exist
    if not cldf_path.exists():
        raise FileNotFoundError(f"CLDF directory not found: {cldf_path}")

    parameters_file = cldf_path / "parameters.csv"
    forms_file = cldf_path / "forms.csv"
    languages_file = cldf_path / "languages.csv"

    for file_path in [parameters_file, forms_file, languages_file]:
        if not file_path.exists():
            raise FileNotFoundError(f"Required file not found: {file_path}")

    # Step 1: Parse parameters to identify 40 core concepts
    core_concepts = _parse_core_concepts(parameters_file)

    # Step 2: Parse languages for metadata
    languages = _parse_languages(languages_file)

    # Step 3: Parse forms and filter to core concepts
    concept_data = _parse_forms(forms_file, core_concepts, languages)

    return concept_data


def _parse_core_concepts(parameters_file: Path) -> Dict[str, str]:
    """
    Parse parameters.csv to extract concept IDs and names for core concepts.

    Core concepts are identified by names starting with '*' (e.g., "*water").

    Returns:
        Dict mapping concept_id (e.g., "75") to name (e.g., "*water")
    """
    core_concepts = {}

    with open(parameters_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            concept_id = row["ID"]
            name = row["Name"]

            # Filter to starred concepts only
            if name.startswith("*"):
                core_concepts[concept_id] = name

    if len(core_concepts) != 40:
        raise ValueError(
            f"Expected 40 core concepts, found {len(core_concepts)}. "
            "ASJP dataset may be corrupted or version mismatch."
        )

    return core_concepts


def _parse_languages(languages_file: Path) -> Dict[str, LanguageData]:
    """
    Parse languages.csv to extract language metadata.

    Returns:
        Dict mapping language_id to LanguageData
    """
    languages = {}

    with open(languages_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            language_id = row["ID"]
            name = row["Name"]
            family = row.get("Family", "")
            iso_code = row.get("ISO639P3code", "") or None

            # Parse coordinates (may be empty)
            lat_str = row.get("Latitude", "").strip()
            lon_str = row.get("Longitude", "").strip()
            coordinates = None
            if lat_str and lon_str:
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    coordinates = (lat, lon)
                except ValueError:
                    # Skip malformed coordinates
                    pass

            languages[language_id] = LanguageData(
                language_id=language_id,
                name=name,
                family=family,
                iso_code=iso_code,
                coordinates=coordinates,
            )

    return languages


def _parse_forms(
    forms_file: Path, core_concepts: Dict[str, str], languages: Dict[str, LanguageData]
) -> Dict[str, ConceptData]:
    """
    Parse forms.csv and extract forms for core concepts.

    Handles edge cases:
    - Missing Segments column: skip form
    - Empty Segments: skip form
    - Multiple forms per language-concept: keep all

    Returns:
        Dict mapping concept_id to ConceptData
    """
    # Initialize ConceptData for each core concept
    concept_data = {
        concept_id: ConceptData(concept_id=concept_id, name=name, forms=[])
        for concept_id, name in core_concepts.items()
    }

    with open(forms_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            language_id = row["Language_ID"]
            concept_id = row["Parameter_ID"]
            raw_value = row.get("Value", "")
            segments_str = row.get("Segments", "").strip()

            # Filter to core concepts only
            if concept_id not in core_concepts:
                continue

            # Skip if Segments is missing or empty
            if not segments_str:
                continue

            # Parse space-separated IPA segments
            ipa_segments = segments_str.split()

            # Skip if segments list is empty after splitting
            if not ipa_segments:
                continue

            # Create FormData
            form = FormData(
                language_id=language_id,
                concept_id=concept_id,
                raw_value=raw_value,
                ipa_segments=ipa_segments,
            )

            # Add to concept
            concept_data[concept_id].forms.append(form)

    return concept_data
