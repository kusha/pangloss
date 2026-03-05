# Data Module: speakers.py

This module provides global speaker count data extracted from CLDR and ASJP sources.

## Quick Start

```python
from pangloss.data.speakers import load_speaker_counts

# Load speaker counts (uses cache if available)
speakers = load_speaker_counts()

# Look up speakers for a language
english_speakers = speakers.get("ENGLISH")  # 1,733,824,666
mandarin_speakers = speakers.get("zho")     # 1,325,522,922
```

## Data Sources

1. **CLDR** (primary): Unicode Common Locale Data Repository
   - Source: `supplementalData.xml` territoryInfo
   - Data: Language populations by territory
   - Quality: High (based on census data)
   - Coverage: ~720 language codes

2. **ASJP** (fallback): Automated Similarity Judgment Program
   - Source: `raw/lists.txt` metadata
   - Data: Direct population estimates
   - Quality: Good (ASJP database standards)
   - Coverage: ~10,500 languages

## Coverage

- **Total Languages**: 10,719 entries with speaker counts
- **ASJP Coverage**: 91.2% (10,526 of 11,540 ASJP entries)
- **Cache**: `data/speakers.json` (240KB)

## Language ID Formats

The module returns speaker counts for:
- **ASJP IDs**: `ENGLISH`, `SPANISH`, `HINDI`, etc. (when mapped via ISO 639-3)
- **ISO 639-3 codes**: `eng`, `spa`, `hin`, etc. (fallback)
- **ASJP variant IDs**: `MANDARIN_BEIJING`, `MANDARIN_SHANGHAI`, etc.

## API

### `load_speaker_counts(cldr_xml_path=None, cache_path=None) -> Dict[str, int]`

Load speaker counts with automatic caching.

**Parameters**:
- `cldr_xml_path`: Path to CLDR supplementalData.xml (default: `/tmp/supplementalData.xml`)
- `cache_path`: Path to cache JSON (default: `data/speakers.json`)

**Returns**: Dict mapping language ID to speaker count

**Example**:
```python
speakers = load_speaker_counts()
print(speakers["ENGLISH"])  # 1733824666
```

### `get_speakers_for_asjp_language(asjp_id, speakers_dict) -> Optional[int]`

Look up speaker count for an ASJP language variant (handles dialect variants).

**Parameters**:
- `asjp_id`: ASJP language ID
- `speakers_dict`: Result from `load_speaker_counts()`

**Returns**: Speaker count or None if not found

**Example**:
```python
speakers = load_speaker_counts()
count = get_speakers_for_asjp_language("A53_BAFIA_RIKPA", speakers)
```

## Implementation Details

### CLDR Processing
1. Download `supplementalData.xml` from GitHub (Unicode repository)
2. Parse `territoryInfo` section
3. Extract language population percentages per territory
4. Multiply by territory population to get absolute counts
5. Aggregate across territories

### ASJP Fallback
1. Parse `raw/lists.txt` format (language header + stats line)
2. Extract population number from stats line
3. Use for languages not covered by CLDR
4. Preserves dialect variants separately

### Caching Strategy
- First load: Parses both CLDR and ASJP data
- Subsequent loads: Uses cached JSON
- Cache invalidation: Delete `data/speakers.json` to regenerate

## Data Quality

- **No zero values**: All entries have >0 speakers
- **Range**: 1 to 1,733,824,666 speakers
- **Validation**: All major languages verified (English >1B, Mandarin >1B, etc.)
- **Sanity**: No anomalies or impossible values

## Design Decisions

See `.sisyphus/notepads/pangloss-mvp/decisions.md` for:
- Full mapping strategy documentation
- Coverage improvement details (4.6% → 91.2%)
- Rationale for CLDR + ASJP hybrid approach
- Known limitations and future enhancements
