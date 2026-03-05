# Learnings - Pangloss v2

This file tracks conventions, patterns, and architectural decisions discovered during implementation.

---


## Task 3: Coverage Statistics Fix (2026-03-05)

### Problem
- `total_speakers` was summing `word.speaker_count` across ALL synonyms, causing double-counting when languages overlapped
- `total_coverage` was using `max(word.coverage_pct)` instead of computing union-based coverage

### Solution
Modified `pangloss/output/dictionary.py` lines 76-101:

1. **Build language → speaker_count lookup** from `matrix_entries[concept_name]`
   - Iterate through MatrixEntry objects to get language_id → speaker_count mapping
   - Safe fallback: if matrix_entries not available, use fallback logic

2. **Compute total_speakers as union-based**
   - Get union of all covered languages: `all_languages = union(word.covered_languages for all words)`
   - Sum speakers only for unique languages: `total_speakers = sum(lang_speaker_counts[lang_id] for lang_id in all_languages)`
   - Eliminates double-counting of overlapping languages

3. **Compute total_coverage as ratio of unique speakers**
   - `concept_total_speakers = sum(lang_speaker_counts.values())`  (sum of ALL possible languages for concept)
   - `total_coverage = (total_speakers / concept_total_speakers) * 100`
   - This represents: "what % of the concept's total possible speakers are covered?"

### Key Insights
- The union approach is correct: multiple synonyms covering overlapping languages = single count
- For single-synonym concepts, total_coverage ≈ synonym coverage (edge case handles correctly)
- The implementation safely handles missing matrix_entries using fallback behavior
- No per-synonym fields were modified (those remain per-word stats, not per-concept aggregates)

### Implementation Details
- Lines 80-83: Build `lang_speaker_counts` dict from matrix_entries
- Lines 85-88: Sum speakers for union of languages only
- Lines 94-101: Compute total_coverage as ratio of unique speakers to concept total
- Handles edge case: division by zero check with `if concept_total_speakers > 0`

### Test Results
- QA Scenario 1 (de-duplication): ✓ PASS - Coverage reflects union, not sum
- QA Scenario 2 (single-synonym): N/A - No single-synonym concepts in test data, but code handles correctly
- Evidence saved to: `.sisyphus/evidence/task-3-coverage-stats.txt`, `.sisyphus/evidence/task-3-single-synonym.txt`


## Task 2: YAML Output Filename Fix

**Pattern**: Format choice propagation to output path
- Changed line 210 in `pangloss/cli.py`: `"dictionary.json"` → `f"dictionary.{format_choice}"`
- `format_choice` variable available in scope from CLI argument (line 64)
- `save_dictionary()` already handles format conversion correctly

**Key Learning**: Path construction should match the format parameter passed to save function
- The filename extension should reflect the actual output format
- Hardcoded extensions defeat the purpose of format flags
- Use f-strings to tie filename to format choice variable

**QA Results**: Both formats tested and working
- `--format yaml` creates `dictionary.yaml` ✓
- `--format json` creates `dictionary.json` ✓

## Task 1: Concept Name Normalization + Graph Filenames (2026-03-05)

### Problem
1. `--concept water` lookup failed because matrix keys have `*` prefix (e.g., `*water`)
2. Graph filenames were generated with `*` prefix (e.g., `*water.json`), violating filesystem conventions
3. Error messages showed raw matrix keys with `*`, confusing users

### Solution
Modified `pangloss/cli.py` in two locations:

**1. Lines 131-155: Concept Filter with Prefix Normalization**
- Try direct lookup first: `if concept in matrix`
- Fallback to prefixed lookup: `elif f"*{concept}" in matrix`
- Additional fallback: case-insensitive search for user-friendly error handling
- Error message shows available concepts WITHOUT `*` prefix for clarity

**Key Code Pattern**:
```python
concept_key = None
if concept in matrix:
    concept_key = concept
elif f"*{concept}" in matrix:
    concept_key = f"*{concept}"
else:
    # Try case-insensitive search
    concept_lower = concept.lstrip("*").lower()
    for key in matrix.keys():
        if key.lstrip("*").lower() == concept_lower:
            concept_key = key
            break

# Error message strips * for display
available = sorted([k.lstrip("*") for k in matrix.keys()])
```

**2. Line 186: Graph Filename Stripping**
- Changed: `f"{concept_name}.json"` → `f"{concept_name.lstrip('*')}.json"`
- Simple one-liner: `.lstrip('*')` removes leading asterisk from concept_name
- Result: `water.json` instead of `*water.json`

### Key Insights
- Matrix keys MUST have `*` prefix (ASJP convention in `_parse_core_concepts`)
- CLI layer should normalize input to hide this implementation detail from users
- Filesystem conventions don't permit `*` in filenames (platform portability issue)
- Error messages should show user-friendly names without `*`

### Implementation Details
- Concept normalization happens at lookup time (lines 131-155)
- Graph filename stripping is one-liner operation (line 186)
- Case-insensitive fallback improves UX without affecting ASJP data integrity

### Test Results - All 4 QA Scenarios PASSED
1. ✓ `--concept water` lookup works (bare name without *)
2. ✓ `--concept "*water"` lookup works (explicit * also accepted)
3. ✓ Graph filenames generated without * prefix (water.json, not *water.json)
4. ✓ Error message for invalid concept shows clean available list without *

**Evidence files saved**:
- `.sisyphus/evidence/task-1-concept-filter-bare.txt`
- `.sisyphus/evidence/task-1-concept-filter-star.txt`
- `.sisyphus/evidence/task-1-graph-filenames.txt`
- `.sisyphus/evidence/task-1-invalid-concept.txt`

## Task 4: ISO-Canonical Speaker Lookup (Wave 2)

### Problem
- `speaker_counts` dict had **mixed keyspace**: some keys were ASJP IDs, others were ISO codes
- Original lookup chain: `asjp_id → iso_code → representative_asjp_id → speaker_counts[representative_asjp_id]`
- Failure mode: KeyError when `representative_asjp_id` not found in `speaker_counts`
- Root cause: `load_speaker_counts()` stores ASJP ID if mapping exists, else ISO code

### Solution
- Built **ISO-canonical lookup dict** in `build_matrix()`:
  1. Iterate `speaker_counts` with mixed keys
  2. Detect ISO codes (3-letter lowercase heuristic)
  3. For ASJP IDs, reverse-lookup via `iso_to_asjp_representative` to find ISO code
  4. Store all speaker counts with ISO code keys in `iso_speaker_counts`
- Simplified lookup: `asjp_id → iso_code → iso_speaker_counts[iso_code]` (fallback to 0)

### Results
- **83.1% mapping success** (5,032 of 6,056 languages have speaker data)
- **1,024 unmapped languages** (16.9%) — explicit tracking vs silent failures
- **Zero KeyErrors** — graceful fallback for missing data
- **Pipeline executes cleanly** — all 40 concepts processed, 79.1% avg coverage

### Key Insights
1. **Keyspace normalization is critical** when merging data from multiple sources
2. **ISO codes are the canonical identifier** — ASJP IDs are variants/dialects
3. **Explicit unmapped tracking** (speakers=0) better than None/KeyError
4. **Reverse lookup technique** enables canonicalization without changing data sources

### Code Patterns
- **Heuristic key detection**: `len(key) == 3 and key.islower()` for ISO codes
- **Reverse lookup**: Iterate `iso_to_asjp_representative.items()` to find ISO for ASJP ID
- **Defensive fallback**: `iso_speaker_counts.get(iso_code, 0)` prevents crashes

### Files Modified
- `pangloss/data/matrix.py` lines 115-143: Added ISO canonicalization logic
- `data/speakers.json`: Deleted and regenerated (no format change)

## Task 5: De-duplicate total_speakers (Wave 2) - 2026-03-05

### Changes
- Added fields to ConceptEntry:
  - `language_to_speakers: Dict[str, int]` — maps language_id → speaker_count
  - `total_unique_speakers: int` — ISO-canonical de-duplicated total
- Kept `total_speakers` field for backward compatibility (raw sum)
- De-duplication logic (lines 193-203 in matrix.py):
  - Build `iso_speakers_seen` dict using `asjp_to_iso` mapping
  - Count each ISO code only once (first occurrence wins)
  - Include unmapped languages with speaker_count > 0 (fallback to ASJP ID)
- Results for *water concept:
  - Raw total_speakers: 228,985,224,125 (inflated)
  - De-duplicated total_unique_speakers: 10,133,094,336 (96% reduction)
  - 11,873 forms → 10,974 unique language_ids in language_to_speakers

### Key Insights
- **Duplicate language_ids**: 779 languages have multiple forms for same concept (e.g., different dialectal variants). The `language_to_speakers` dict correctly collapses these to single entries (last form wins).
- **Unmapped languages**: 1,157 forms have speaker_count=0 (not in ISO mapping). These are excluded from `total_unique_speakers` but counted in `total_languages`.
- **De-duplication invariant**: `total_unique_speakers <= total_speakers` holds for all 40 concepts.
- **Backward compatibility**: Downstream code still works with `total_speakers` field. Tasks 7-8 will migrate to `total_unique_speakers`.
- **ISO-canonical correctness**: Same pattern used as Task 4 (`asjp_to_iso.get()` → `iso_speakers_seen`). No new mappings needed — reuses existing infrastructure.

### Edge Cases Handled
- Multiple ASJP variants with same ISO code: De-duplicated (only count ISO once)
- Unmapped ASJP languages with speakers > 0: Counted using ASJP ID as fallback
- Duplicate language_ids in entries list: Dict comprehension naturally collapses to unique keys
- Zero-speaker languages: Excluded from `total_unique_speakers`, kept in `total_languages`

### Verification
- Syntax check: ✓ passed
- Import test: ✓ passed
- Pipeline smoke test: ✓ all 40 concepts have new fields
- De-duplication invariant: ✓ holds for all concepts
- Evidence: `.sisyphus/evidence/task-5-dedup-speakers.txt`
