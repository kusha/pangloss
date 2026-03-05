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
