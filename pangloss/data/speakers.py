"""
Parse CLDR supplemental data to extract global speaker counts per language.

Strategy:
1. Parse CLDR territoryInfo to extract language populations per territory
2. Create ISO 639-3 lookup table for CLDR language codes (BCP 47) ↔ ASJP ISO 639-3 mapping
3. Aggregate territory-level data to get total speakers per language (native + L2)
4. Map ASJP languages using ISO 639-3 as bridge
5. Fallback: for unmapped languages, parse ASJP raw/lists.txt metadata
6. Cache processed data as JSON for fast loading
"""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Union

# ISO 639-3 to BCP 47 mapping for major languages
# This bridges CLDR (BCP 47) and ASJP (ISO 639-3) codes
ISO_639_3_TO_BCP47 = {
    "eng": "en",
    "spa": "es",
    "fra": "fr",
    "deu": "de",
    "ita": "it",
    "por": "pt",
    "rus": "ru",
    "jpn": "ja",
    "zho": "zh",  # Mandarin/Chinese
    "ara": "ar",
    "hin": "hi",
    "ben": "bn",
    "pun": "pa",
    "jav": "jv",
    "vie": "vi",
    "tur": "tr",
    "urd": "ur",
    "guj": "gu",
    "pol": "pl",
    "ukr": "uk",
    "mrh": "mr",
    "tam": "ta",
    "tel": "te",
    "kan": "kn",
    "mal": "ml",
    "tha": "th",
    "mya": "my",
    "khm": "km",
    "nld": "nl",
    "swe": "sv",
    "ell": "el",
    "hun": "hu",
    "ces": "cs",
    "ron": "ro",
    "dan": "da",
    "fin": "fi",
    "nno": "nn",
    "nob": "nb",
    "kat": "ka",
    "eus": "eu",
    "isl": "is",
    "hrv": "hr",
    "srp": "sr",
    "slk": "sk",
    "slv": "sl",
    "bul": "bg",
    "fas": "fa",
    "kok": "kok",
    "sin": "si",
    "fil": "fil",
    "kat": "ka",
}

# Reverse mapping: BCP 47 to ISO 639-3
BCP47_TO_ISO_639_3 = {v: k for k, v in ISO_639_3_TO_BCP47.items()}


def load_cldr_data(cldr_xml_path: str) -> Dict[str, int]:
    """
    Parse CLDR territoryInfo and aggregate language speaker counts.
    Returns dict: {iso639_3_code: total_speakers}
    """
    language_speakers = {}

    try:
        tree = ET.parse(cldr_xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing CLDR XML: {e}")
        return {}

    # Extract territoryInfo section
    territory_info = root.find("territoryInfo")
    if territory_info is None:
        print("No territoryInfo found in CLDR data")
        return {}

    # Iterate through territories
    for territory in territory_info.findall("territory"):
        population_str = territory.get("population", "0")
        try:
            territory_population = int(population_str)
        except ValueError:
            territory_population = 0

        if territory_population == 0:
            continue

        # Iterate through languages in this territory
        for lang_pop in territory.findall("languagePopulation"):
            lang_code = lang_pop.get("type", "")
            pop_percent_str = lang_pop.get("populationPercent", "0")

            try:
                pop_percent = float(pop_percent_str)
            except ValueError:
                pop_percent = 0.0

            if pop_percent == 0 or not lang_code:
                continue

            # Calculate absolute speaker count for this language in this territory
            speakers = int(territory_population * pop_percent / 100)

            # Normalize BCP 47 code (strip script tags like "uz_Arab" -> "uz")
            base_code = lang_code.split("_")[0]

            # Convert to ISO 639-3 if we have a mapping
            iso_639_3_code = BCP47_TO_ISO_639_3.get(base_code, base_code)

            # Aggregate
            language_speakers[iso_639_3_code] = (
                language_speakers.get(iso_639_3_code, 0) + speakers
            )

    return language_speakers


def load_asjp_raw_speakers() -> Dict[str, int]:
    """
    Parse ASJP raw/lists.txt file to extract population data.
    Format: Each language has header line, followed by stats line with population number.
    """
    asjp_speakers = {}
    raw_path = (
        Path(__file__).parent.parent.parent / "data" / "asjp" / "raw" / "lists.txt"
    )

    if not raw_path.exists():
        print(f"ASJP raw/lists.txt not found at {raw_path}")
        return {}

    try:
        with open(raw_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line and line[0].isupper() and "{" in line and "|" in line:
                lang_name = line.split("{")[0].strip()

                if i + 1 < len(lines):
                    stats_line = lines[i + 1].strip()
                    parts = stats_line.split()

                    if len(parts) >= 4:
                        try:
                            population = int(parts[3])
                            if population > 0:
                                asjp_speakers[lang_name] = population
                        except (ValueError, IndexError):
                            pass

                i += 1
            else:
                i += 1
    except Exception as e:
        print(f"Error loading ASJP raw/lists.txt: {e}")

    return asjp_speakers


def load_asjp_languages() -> Dict[str, str]:
    """
    Load ASJP languages.csv and return mapping of ISO 639-3 codes to first ASJP language ID.

    Note: ASJP has multiple entries (dialects/variants) per ISO 639-3 code.
    We map each ISO code to its first ASJP ID encountered for speaker aggregation.
    """
    asjp_map = {}
    csv_path = (
        Path(__file__).parent.parent.parent / "data" / "asjp" / "cldf" / "languages.csv"
    )

    if not csv_path.exists():
        print(f"ASJP languages.csv not found at {csv_path}")
        return {}

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                iso_code = row.get("ISO639P3code", "").strip()
                asjp_id = row.get("ID", "").strip()

                if iso_code and asjp_id:
                    if iso_code not in asjp_map:
                        asjp_map[iso_code] = asjp_id
    except Exception as e:
        print(f"Error loading ASJP languages.csv: {e}")

    return asjp_map


def get_all_asjp_iso_mappings() -> Dict[str, str]:
    """
    Load ASJP languages.csv and return mapping of ALL ASJP IDs to their ISO 639-3 codes.

    This allows looking up speaker counts for any ASJP language variant.
    """
    asjp_to_iso = {}
    csv_path = (
        Path(__file__).parent.parent.parent / "data" / "asjp" / "cldf" / "languages.csv"
    )

    if not csv_path.exists():
        return {}

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                iso_code = row.get("ISO639P3code", "").strip()
                asjp_id = row.get("ID", "").strip()
                if iso_code and asjp_id:
                    asjp_to_iso[asjp_id] = iso_code
    except Exception as e:
        print(f"Error loading ASJP languages.csv: {e}")

    return asjp_to_iso


def get_speakers_for_asjp_language(
    asjp_id: str, speakers_dict: Dict[str, int]
) -> Optional[int]:
    """
    Look up speaker count for an ASJP language variant.

    Args:
        asjp_id: ASJP language ID
        speakers_dict: Result from load_speaker_counts()

    Returns:
        Speaker count if available, None otherwise.
    """
    asjp_to_iso = get_all_asjp_iso_mappings()
    iso_code = asjp_to_iso.get(asjp_id)

    if iso_code is None:
        return None

    asjp_map = load_asjp_languages()
    representative_asjp_id = asjp_map.get(iso_code)

    if representative_asjp_id:
        return speakers_dict.get(representative_asjp_id)
    else:
        return speakers_dict.get(iso_code)


def load_speaker_counts(
    cldr_xml_path: Optional[Union[str, Path]] = None,
    cache_path: Optional[Union[str, Path]] = None,
) -> Dict[str, int]:
    """
    Load speaker counts for languages, preferring cached JSON if available.

    Args:
        cldr_xml_path: Path to supplementalData.xml (defaults to /tmp/supplementalData.xml)
        cache_path: Path to speakers.json cache (defaults to data/speakers.json)

    Returns:
        dict: {language_id: total_speakers} mapped to ASJP language IDs where possible.
        For languages with multiple ASJP variants, returns ISO code as fallback.
    """
    if cldr_xml_path is None:
        cldr_xml_path = "/tmp/supplementalData.xml"
    if cache_path is None:
        cache_path = Path(__file__).parent.parent.parent / "data" / "speakers.json"

    cldr_xml_path = Path(cldr_xml_path)
    if isinstance(cache_path, str):
        cache_path = Path(cache_path)

    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache from {cache_path}: {e}")

    iso_speakers = load_cldr_data(str(cldr_xml_path))
    asjp_map = load_asjp_languages()
    raw_asjp_speakers = load_asjp_raw_speakers()

    result = {}

    for iso_code, speaker_count in iso_speakers.items():
        asjp_id = asjp_map.get(iso_code)
        if asjp_id:
            result[asjp_id] = speaker_count
        else:
            result[iso_code] = speaker_count

    for asjp_id, speaker_count in raw_asjp_speakers.items():
        if asjp_id not in result:
            result[asjp_id] = speaker_count

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not cache results to {cache_path}: {e}")

    return result


if __name__ == "__main__":
    # Test the module
    speakers = load_speaker_counts()
    print(f"Total languages with speaker counts: {len(speakers)}")

    # Show top languages
    sorted_langs = sorted(speakers.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 20 languages by speaker count:")
    for lang_id, count in sorted_langs[:20]:
        print(f"  {lang_id}: {count:,}")

    # Verify major languages
    print("\nMajor language checks:")
    for asjp_id in ["ENGLISH", "MANDARIN_CHINESE", "SPANISH"]:
        count = speakers.get(asjp_id, 0)
        print(f"  {asjp_id}: {count:,}")
