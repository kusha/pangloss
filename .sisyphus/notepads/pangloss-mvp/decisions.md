# Pangloss MVP - Architectural Decisions

## 1. Click Framework for CLI

**Decision**: Use Click for command-line interface
**Rationale**: 
- Industry-standard Python CLI framework
- Decorator-based, readable syntax
- Automatic help generation and option parsing
- Group/command structure matches Pangloss workflow

## 2. Modern Packaging (pyproject.toml)

**Decision**: Use `pyproject.toml` instead of `setup.py`
**Rationale**:
- PEP 517/518 standard approach (future-proof)
- Cleaner, single-file configuration
- Supports modern build systems
- Easier dependency management

## 3. Modular Subpackage Design

**Decision**: Four independent submodules (data, graph, algo, output)
**Rationale**:
- Separation of concerns: data handling, graph ops, algorithms, export
- Independent development/testing per module
- Clear responsibility boundaries for future contributors

## 4. Version Constraint: Python 3.10+

**Decision**: Set minimum to Python 3.10 (not 3.11)
**Rationale**:
- 3.10 widely available in production environments
- 3.11+ would break on systems with earlier Python versions
- Can enforce 3.11 in future if specific features needed (match expressions)

## 5. No Version Pinning for Dependencies

**Decision**: Leave networkx, click, pyyaml unpinned
**Rationale**:
- MVP should support recent versions of standard libraries
- Version pinning increases maintenance burden
- Can add specific constraints if compatibility issues arise

## 6. Dual Version Location

**Decision**: Store version in both `__init__.py` and `pyproject.toml`
**Rationale**:
- Single source of truth for `pangloss.__version__`
- `pyproject.toml` required by build system
- Duplication is minimal, acceptable trade-off for clarity

## 7. Minimal CLI Stub

**Decision**: Include basic `version` and `analyze` commands as examples
**Rationale**:
- Demonstrates Click usage pattern for future commands
- Provides entry point for extending functionality
- Avoids over-engineering before requirements solidify

## Phoneme Normalization: Length Marker Strategy (Task 4)

**Decision**: Length markers (ː, U+02D0) are PRESERVED during normalization.

**Rationale**:
- Vowel length is phonemically distinctive in many languages (e.g., Finnish, Japanese, Arabic)
- /aː/ and /a/ represent different phonemes, not orthographic variants
- Stripping length would cause false matches between phonemically distinct words
- Example: Finnish "tuli" (fire) vs "tuuli" (wind) — /tuli/ vs /tuːli/

**Alternative considered**: Normalize all length markers to single phonemes
- Rejected: Would lose phonemic information critical for language identification

**Implementation**:
- Length marker (ː) passes through normalization unchanged
- ASCII colon (:) is mapped to IPA length marker (ː) for consistency
- Documented in `pangloss/data/phonemes.py` module docstring

**Date**: 2026-03-05

## 8. Speaker Count Data Extraction: CLDR + ASJP Mapping (Task 3)

**Decision**: Use CLDR territoryInfo for speaker counts, map to ASJP via ISO 639-3

**Strategy**:
1. Parse CLDR supplementalData.xml territoryInfo section
2. Extract language populations per territory by percentage
3. Aggregate to get total speakers per ISO 639-3 code
4. Create BCP 47 ↔ ISO 639-3 lookup table (50 major language mappings)
5. Map languages to ASJP IDs via ISO code
6. For unmapped languages, fallback to ISO code as ID
7. Cache results as JSON for fast loading

**Rationale**:
- CLDR is free, comprehensive, and officially maintained by Unicode
- Territory-level population data allows aggregation of native + L2 speakers
- ASJP has 11,540 entries (dialects/variants) but only 6,135 unique ISO codes
- Strategy: Pick first ASJP ID per ISO code to avoid duplication
- Fallback to ISO code preserves unmapped language data

**Coverage Achieved**:
- 720 total language entries with speaker counts
- 509 languages mapped to ASJP IDs (4.6% of 11,540 ASJP entries)
- 211 languages using ISO code fallback
- Major languages verified: English (1.7B), Mandarin (1.3B), Spanish (508M)
- All speaker counts plausible and non-zero

**Data Quality**:
- Min speakers: 1 (rare languages in border regions)
- Max speakers: 1,733,824,666 (English)
- No anomalies or suspicious values

**Implementation**:
- Module: `pangloss/data/speakers.py`
- Cache: `data/speakers.json`
- Public API: `load_speaker_counts() -> dict[str, int]`

**Limitations**:
- CLDR does not have detailed L2/dialect breakdowns
- Coverage is 4.6% because ASJP has many dialect variants
- Some territories may have outdated population estimates
- Script variants (e.g., "uz_Arab") are normalized to base code

**Date**: 2026-03-05

### Integration with ASJP Raw Data (Fallback)

**Enhancement**: Added fallback to ASJP raw/lists.txt when CLDR data insufficient.

**Why**: CLDR alone provided only 4.6% coverage (527/11,540 ASJP languages)

**Strategy**:
1. Parse ASJP raw/lists.txt file (lists.txt contains metadata for all ASJP languages)
2. Extract population number from stats line following language header
3. Merge ASJP raw data with CLDR-derived data
4. ASJP raw data is only used if language not already in CLDR results

**Result**:
- Coverage increased from 4.6% to 91.2% (10,526/11,540 ASJP languages)
- Total languages with counts: 10,719
- All major languages verified with plausible counts
- No data loss: CLDR quality data (native + L2 from territories) preferred, ASJP raw used as fallback

**Data Quality Trade-off**:
- CLDR data is more accurate (aggregated from population statistics)
- ASJP raw data is estimated (from original ASJP database)
- Merging strategy prioritizes CLDR when available, falls back to ASJP for rare languages

**Date**: 2026-03-05
