# Pangloss v2: Bug Fixes, Coverage Algorithm, Collision Detection, Fuzzy Matching, Matrix Caching

## TL;DR

> **Quick Summary**: Fix 3 known bugs, overhaul the coverage algorithm (5 interconnected scoring/counting fixes), add collision detection between concepts, add fuzzy phoneme matching via articulatory feature groups, and add matrix caching with hash-based invalidation.
> 
> **Deliverables**:
> - 3 bug fixes (concept name normalization, coverage stats, YAML filename)
> - Coverage algorithm overhaul across 5 modules (targeting significant improvement over 36.25% baseline)
> - Collision detection report (exact + near-collision via SequenceMatcher)
> - Fuzzy phoneme matching (articulatory feature groups in convergence/generator)
> - Matrix caching with SHA256-based invalidation
> - CLI tuning knobs for key parameters
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Task 1-3 (bugs) → Task 4-8 (coverage) → Task 9 (collision) → Task 10-11 (fuzzy) → Task 12 (caching) → Task 13 (pipeline verification) → F1-F4

---

## Context

### Original Request
User requested 5 sequential improvements: (1) Fix 3 bugs, (2) Improve coverage algorithm, (3) Add collision detection, (4) Add fuzzy phoneme matching, (5) Add matrix caching. User directive: "do not ask me for help until you are done."

### Interview Summary
**Key Discussions**:
- MVP is complete (17/17 tasks, commit `e54a55a`). 40 Swadesh concepts, 771 synonyms, 36.25% average coverage.
- 3 bugs with exact locations: concept name `*` prefix handling (cli.py:131-139), coverage stats double-counting (dictionary.py:76-86 + root cause in matrix.py:165), YAML filename hardcoded (cli.py:210).
- Coverage algorithm has 5 interconnected bottlenecks across speakers.py, convergence.py, generator.py, selector.py, cli.py.
- User previously set target: "90% absolute coverage, but it should be configurable."

**Research Findings**:
- `speaker_counts` returns mixed keyspace (ASJP IDs + ISO codes). `matrix.py` lookup chain frequently fails → `speakers=0` for many languages.
- `convergence.py:111`: `score = depth * speaker_count` overweights mega-language clusters.
- `generator.py:52-56`: `calculate_score` returns `speakers * ((prefix_len * 2) + suffix_len)` — length REWARD, not penalty.
- `selector.py:128-134`: proportional speaker estimate wildly wrong for skewed distributions.
- `dictionary.py:86`: `total_coverage = max(coverage_pct)` instead of union. `total_speakers` sums per-word (double-counts overlap).
- `matrix.py:165`: `total_speakers = sum(entry.speaker_count)` double-counts same ISO language across ASJP variants.
- Concept names all start with `*` (e.g., `*water`). Graph filenames include `*` prefix (glob-unfriendly).

### Metis Review
**Identified Gaps** (addressed):
- Root cause of total_speakers inflation is `matrix.py:165`, not just `dictionary.py` → fixed in Task 5
- `log(0)` risk when changing scoring formula → guarded with `log1p` or `max(speaker_count, 1)`
- `speakers.json` cache becomes stale after keyspace fix → handled in Task 4 (delete + regenerate)
- Graph filenames with `*` are glob-unfriendly → fixed alongside concept name normalization in Task 1
- Collision detection must check BOTH transliteration form AND IPA, BOTH within-concept and cross-concept → specified in Task 9
- Selector's backward inference from `coverage_pct` (line 93-96) must be updated when coverage computation changes → handled in Task 8
- `pickle.load()` security concerns → use JSON for caching instead
- Multi-character phonemes (tʃ, dʒ) must be handled as units in fuzzy matching → specified in Task 10

---

## Work Objectives

### Core Objective
Fix known bugs, dramatically improve coverage from 36.25% baseline, add collision detection and fuzzy phoneme matching for richer output, and add matrix caching for performance.

### Concrete Deliverables
- Bug-free `--concept` filter, correct coverage stats, correct YAML filename
- Overhauled scoring in convergence, generator, and selector modules
- De-duplicated speaker counts at matrix level (ISO-canonical)
- CLI flags: `--convergence-k`, `--max-word-length`, `--min-speakers`
- New `pangloss/algo/collisions.py` module with detection report in dictionary output
- Fuzzy phoneme matching via articulatory feature groups in `pangloss/data/phonemes.py`
- Matrix caching in `pangloss/data/matrix.py` with hash-based invalidation
- End-to-end pipeline verification with before/after metrics

### Definition of Done
- [ ] `pangloss generate --concept water --verbose` succeeds (handles `*` prefix)
- [ ] `pangloss generate --format yaml` creates `output/dictionary.yaml` (not `.json`)
- [ ] `avg_coverage_pct` in `summary.json` > 36.25% (baseline)
- [ ] No concept has 0 synonyms
- [ ] Collision report present in dictionary output with structured data
- [ ] Second pipeline run with caching is measurably faster than first
- [ ] All 40 concepts processed without errors

### Must Have
- Bug fixes for all 3 reported issues
- De-duplicated speaker counts (ISO-canonical) at matrix level
- `log1p` or equivalent guard for speaker_count=0 in scoring formulas
- Collision detection for both exact and near-collisions, both within-concept and cross-concept
- Articulatory feature groups for fuzzy matching (at least: stops, fricatives, nasals, vowels)
- Matrix cache with automatic invalidation when inputs change
- CLI tuning knobs: `--convergence-k`, `--max-word-length`, `--min-speakers`

### Must NOT Have (Guardrails)
- NO changes to `graph/trie.py` — trie structure is correct, bugs are downstream
- NO new external dependencies — use only stdlib (`difflib`, `hashlib`, `json`, `math`)
- NO test framework setup (no pytest) — use verification scripts following `scripts/verify_*.py` pattern
- NO docstring rewriting — existing docstrings are comprehensive
- NO premature abstraction — no "scoring framework", no "cache management layer", no ABC classes
- NO CLI restructuring — add options to existing `generate` command only
- NO changes to `SyntheticWord` dataclass field TYPES — may add new fields if needed
- NO rewriting of `speakers.py` data source loading — fix only the lookup/scoring chain downstream
- NO more than 3 new CLI options
- NO `pickle` for caching — use JSON (security: pickle.load can execute arbitrary code)
- NO graph filename with `*` prefix — strip `*` from concept names in filenames

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None — verification via agent-executed QA scenarios + scripts
- **Framework**: None (follow existing `scripts/verify_*.py` pattern)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI/Pipeline**: Use Bash — Run pipeline commands, parse JSON output, assert fields
- **Module-level**: Use Bash (python REPL) — Import, call functions, compare output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — bug fixes, can run in parallel):
├── Task 1: Fix concept name normalization + graph filenames [quick]
├── Task 2: Fix YAML output filename [quick]
├── Task 3: Fix coverage statistics in dictionary.py [quick]

Wave 2 (After Wave 1 — coverage algorithm overhaul, partially parallel):
├── Task 4: Canonicalize speaker lookup to ISO in matrix.py [unspecified-high]
├── Task 5: De-duplicate total_speakers in matrix.py [unspecified-high]
├── Task 6: Fix convergence scoring formula [unspecified-high]
├── Task 7: Fix generator scoring formula [unspecified-high]
├── Task 8: Fix selector with per-language speaker weights [deep]

Wave 3 (After Wave 2 — new features, partially parallel):
├── Task 9: Add collision detection module + CLI integration [unspecified-high]
├── Task 10: Add articulatory feature groups to phonemes.py [unspecified-high]
├── Task 11: Integrate fuzzy matching into convergence + generator [deep]
├── Task 12: Add matrix caching with hash-based invalidation [unspecified-high]

Wave 4 (After Wave 3 — CLI + integration):
├── Task 13: Add CLI tuning knobs + end-to-end pipeline verification [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — full pipeline run (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: T1-3 → T4-5 → T6-8 → T9 → T10-11 → T12 → T13 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Waves 1 & 3)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1 | — | T4, T13 | 1 |
| T2 | — | T13 | 1 |
| T3 | — | T5, T8, T13 | 1 |
| T4 | T1 | T5, T6, T7, T8 | 2 |
| T5 | T3, T4 | T6, T7, T8, T13 | 2 |
| T6 | T5 | T8, T11, T13 | 2 |
| T7 | T5 | T8, T11, T13 | 2 |
| T8 | T5, T6, T7 | T9, T13 | 2 |
| T9 | T8 | T13 | 3 |
| T10 | — | T11 | 3 |
| T11 | T6, T7, T10 | T13 | 3 |
| T12 | T5 | T13 | 3 |
| T13 | T9, T11, T12 | F1-F4 | 4 |
| F1-F4 | T13 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `quick`, T2 `quick`, T3 `quick`
- **Wave 2**: 5 tasks — T4 `unspecified-high`, T5 `unspecified-high`, T6 `unspecified-high`, T7 `unspecified-high`, T8 `deep`
- **Wave 3**: 4 tasks — T9 `unspecified-high`, T10 `unspecified-high`, T11 `deep`, T12 `unspecified-high`
- **Wave 4**: 1 task — T13 `unspecified-high`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. Fix concept name normalization + graph filenames

  **What to do**:
  - In `pangloss/cli.py` lines 131-139: When `--concept` is provided, normalize it to match matrix keys. Matrix keys have `*` prefix (e.g., `*water`). Try both `concept` and `f"*{concept}"` when looking up. Also handle case-insensitivity.
  - In `pangloss/cli.py` line 171: Strip `*` prefix from concept_name when building graph filenames. Change `graph_path = graphs_path / f"{concept_name}.json"` to `graph_path = graphs_path / f"{concept_name.lstrip('*')}.json"`.
  - Verify the `--concept` filter error message still shows available concepts clearly (stripping `*` for display).

  **Must NOT do**:
  - Do NOT change `asjp.py` or `_parse_core_concepts` — the `*` prefix in concept names is correct per ASJP convention
  - Do NOT change how matrix keys are stored — only fix the CLI lookup layer

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Two small changes in one file (cli.py), well-defined scope
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 13
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `pangloss/cli.py:131-139` — Current `--concept` filter code. The lookup `concept not in matrix` fails because matrix keys are `*water` but user passes `water`.
  - `pangloss/cli.py:171` — Graph filename construction: `graphs_path / f"{concept_name}.json"` creates `*water.json`.
  - `pangloss/data/asjp.py:85-112` — `_parse_core_concepts` shows concept names are stored with `*` prefix from parameters.csv.

  **WHY Each Reference Matters**:
  - `cli.py:131-139`: This is the exact code to modify. The fix adds a fallback: if `concept` not found, try `f"*{concept}"`.
  - `cli.py:171`: This is where `*` gets into filenames. Strip it for filesystem safety.
  - `asjp.py:85-112`: Confirms ALL 40 concepts use `*` prefix, so the `*{concept}` fallback is reliable.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: --concept filter works with bare name
    Tool: Bash
    Preconditions: Pipeline dependencies available (data/asjp/, data/speakers.json)
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate && python -m pangloss generate --concept water --verbose 2>&1`
      2. Assert: exit code is 0
      3. Assert: output contains "✓" (concept processed successfully)
      4. Assert: output contains "water" (concept name in progress output)
    Expected Result: Pipeline processes single concept without error
    Failure Indicators: "Error: Concept 'water' not found" message, non-zero exit code
    Evidence: .sisyphus/evidence/task-1-concept-filter-bare.txt

  Scenario: --concept filter works with * prefix
    Tool: Bash
    Preconditions: Same as above
    Steps:
      1. Run: `python -m pangloss generate --concept "*water" --verbose 2>&1`
      2. Assert: exit code is 0
      3. Assert: output contains "✓"
    Expected Result: Pipeline accepts both `water` and `*water`
    Evidence: .sisyphus/evidence/task-1-concept-filter-star.txt

  Scenario: Graph filenames have no * prefix
    Tool: Bash
    Preconditions: Run full pipeline first
    Steps:
      1. Run: `python -m pangloss generate --verbose 2>&1`
      2. Run: `ls output/graphs/ | head -5`
      3. Assert: NO filename starts with `*`
      4. Assert: files like `water.json`, `fire.json` exist (not `*water.json`)
    Expected Result: All graph filenames are glob-safe (no `*` prefix)
    Failure Indicators: Any filename starting with `*`
    Evidence: .sisyphus/evidence/task-1-graph-filenames.txt

  Scenario: Invalid concept name gives clear error
    Tool: Bash
    Steps:
      1. Run: `python -m pangloss generate --concept nonexistent 2>&1`
      2. Assert: exit code is non-zero
      3. Assert: output contains "not found" and lists available concepts
    Expected Result: Clear error message with available concept list
    Evidence: .sisyphus/evidence/task-1-invalid-concept.txt
  ```

  **Commit**: YES (groups with T2, T3)
  - Message: `fix(cli): handle concept name * prefix and strip * from graph filenames`
  - Files: `pangloss/cli.py`
  - Pre-commit: `python -m pangloss generate --concept water --verbose`

- [x] 2. Fix YAML output filename

  **What to do**:
  - In `pangloss/cli.py` line 210: Change `dictionary_path = str(output_path / "dictionary.json")` to `dictionary_path = str(output_path / f"dictionary.{format_choice}")`.
  - This ensures `--format yaml` creates `dictionary.yaml` instead of `dictionary.json` with YAML content.

  **Must NOT do**:
  - Do NOT change `save_dictionary()` in `dictionary.py` — it already handles format correctly
  - Do NOT change the summary output path (line 224) — it stays as `summary.json`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single line change in one file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 13
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pangloss/cli.py:210` — Hardcoded `"dictionary.json"`. The `format_choice` variable is available in scope (line 64, passed as arg to `generate()`).
  - `pangloss/cli.py:211` — `save_dictionary(dictionary, dictionary_path, format=format_choice)` — already passes format correctly, just the path is wrong.

  **WHY Each Reference Matters**:
  - Line 210 is the exact line to change. Line 211 confirms `format_choice` is used correctly downstream.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: YAML format creates .yaml file
    Tool: Bash
    Preconditions: Pipeline dependencies available
    Steps:
      1. Run: `rm -f output/dictionary.json output/dictionary.yaml`
      2. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate && python -m pangloss generate --format yaml --verbose 2>&1`
      3. Assert: exit code is 0
      4. Assert: `output/dictionary.yaml` exists
      5. Assert: `output/dictionary.json` does NOT exist (unless a previous JSON run left it)
      6. Run: `head -5 output/dictionary.yaml`
      7. Assert: content is valid YAML (not JSON)
    Expected Result: YAML output saves to .yaml extension
    Failure Indicators: File saved as `dictionary.json` with YAML content
    Evidence: .sisyphus/evidence/task-2-yaml-filename.txt

  Scenario: JSON format still creates .json file
    Tool: Bash
    Steps:
      1. Run: `rm -f output/dictionary.json output/dictionary.yaml`
      2. Run: `python -m pangloss generate --format json --verbose 2>&1`
      3. Assert: `output/dictionary.json` exists
      4. Run: `python -c "import json; json.load(open('output/dictionary.json'))"`
      5. Assert: exit code is 0 (valid JSON)
    Expected Result: JSON output unchanged
    Evidence: .sisyphus/evidence/task-2-json-filename.txt
  ```

  **Commit**: YES (groups with T1, T3)
  - Message: `fix(cli): use correct file extension for YAML output`
  - Files: `pangloss/cli.py`

- [x] 3. Fix coverage statistics in dictionary.py

  **What to do**:
  - In `pangloss/output/dictionary.py` lines 76-86: Fix two issues:
    1. **`total_speakers` double-counts**: Currently sums `word.speaker_count` across all synonyms, but overlapping languages get counted multiple times. Fix: use `matrix_entries` (already passed) to build a `lang_id → speaker_count` dict, then compute total as sum of speakers for the UNION of `all_languages` (already computed at line 76-79).
    2. **`total_coverage` uses max instead of union**: Line 86 takes `max(word.coverage_pct)`. Fix: compute `total_coverage` as `(sum_of_unique_speakers / concept_total_speakers) * 100` where `concept_total_speakers` comes from matrix_entries.
  - The `matrix_entries` dict is already available (passed in, used at line 143). Use it to get per-language speaker counts.

  **Must NOT do**:
  - Do NOT change `format_summary()` — it reads from the corrected dictionary output
  - Do NOT change the per-synonym `speaker_count` or `coverage_pct` fields — those are per-word stats
  - Do NOT fix the root cause of speaker inflation in `matrix.py` here — that's Task 5

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Localized fix in one function, well-defined data flow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 5, 8, 13
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pangloss/output/dictionary.py:22-99` — `format_dictionary()` function. Lines 76-86 are the bug area. `matrix_entries` parameter already provides per-concept MatrixEntry lists.
  - `pangloss/data/matrix.py:20-39` — `MatrixEntry` dataclass shows `language_id`, `speaker_count`, `language_family` fields available.
  - `pangloss/algo/generator.py:6-14` — `SyntheticWord` dataclass shows `covered_languages` is `Set[str]` of language IDs.

  **WHY Each Reference Matters**:
  - `dictionary.py:22-99`: This is the function to modify. The fix builds a `lang_id → speakers` lookup from `matrix_entries`, then computes union coverage correctly.
  - `matrix.py:20-39`: Shows what fields are available on `MatrixEntry` for the lookup.
  - `generator.py:6-14`: Shows `covered_languages` contains language IDs that can be looked up in matrix_entries.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Coverage stats are de-duplicated
    Tool: Bash
    Preconditions: Pipeline dependencies available
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate && python -m pangloss generate --verbose 2>&1`
      2. Run: `python -c "
import json
d = json.load(open('output/dictionary.json'))
for c in d['concepts'][:3]:
    print(f\"{c['concept']}: coverage={c['total_coverage']:.1f}%, speakers={c['total_speakers']:,}, synonyms={c['synonym_count']}\")
    # Verify total_speakers <= sum of all matrix entry speakers (no inflation)
    # Verify total_coverage is not just max of individual synonyms
"`
      3. Assert: `total_coverage` values are >= corresponding max individual synonym coverage (union >= max)
      4. Assert: `total_speakers` values are reasonable (not massively inflated by double-counting)
    Expected Result: Coverage stats reflect union of covered languages, not sum or max
    Failure Indicators: `total_coverage` equals exactly `max(synonym.coverage_pct)` — means union calculation not applied
    Evidence: .sisyphus/evidence/task-3-coverage-stats.txt

  Scenario: Coverage stats handle single-synonym concept correctly
    Tool: Bash
    Steps:
      1. Run: `python -c "
import json
d = json.load(open('output/dictionary.json'))
for c in d['concepts']:
    if c['synonym_count'] == 1:
        syn = c['synonyms'][0]
        # For single synonym, total_coverage should equal synonym's coverage
        print(f\"{c['concept']}: total={c['total_coverage']:.1f}%, syn={syn['coverage_pct']:.1f}%\")
        break
"`
      2. Assert: For single-synonym concepts, `total_coverage` approximately equals the synonym's `coverage_pct`
    Expected Result: Single-synonym edge case handled correctly
    Evidence: .sisyphus/evidence/task-3-single-synonym.txt
  ```

  **Commit**: YES (groups with T1, T2)
  - Message: `fix(dictionary): compute coverage as union of languages, not sum/max`
  - Files: `pangloss/output/dictionary.py`

- [ ] 4. Canonicalize speaker lookup to ISO in matrix.py

  **What to do**:
  - In `pangloss/data/matrix.py` lines 115-143: The current lookup chain is: `asjp_id → iso_code (via asjp_to_iso) → representative_asjp_id (via iso_to_asjp_representative) → speaker_counts[representative_asjp_id]`. This fails when `representative_asjp_id` doesn't exist as a key in `speaker_counts`.
  - Root cause: `load_speaker_counts()` in `speakers.py` (lines 311-316) stores results with mixed keys — sometimes ASJP ID, sometimes ISO code. The matrix lookup assumes ASJP ID keys but many are ISO.
  - Fix approach: After `speaker_counts` is loaded, build an **ISO-canonical lookup** in `build_matrix()`:
    1. Use `get_all_asjp_iso_mappings()` (already called at line 115) to get `asjp_id → iso_code`.
    2. Build `iso_speaker_counts: Dict[str, int]` by iterating `speaker_counts` and converting keys to ISO where possible.
    3. For each form in the matrix, look up speakers by: `iso_code = asjp_to_iso.get(form.language_id)` → `speakers = iso_speaker_counts.get(iso_code, 0)`.
  - Delete and regenerate `data/speakers.json` cache after this change (the cache format doesn't change, but downstream expects consistent lookup).

  **Must NOT do**:
  - Do NOT rewrite `load_speaker_counts()` or `load_cldr_data()` — the data sources are correct
  - Do NOT change the `speakers.json` cache format
  - Do NOT add new dependencies

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding the full speaker lookup chain and data flow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Wave 1 completing)
  - **Parallel Group**: Wave 2 (can run with T5 if T5 doesn't depend on this — but T5 does depend on T4)
  - **Blocks**: Tasks 5, 6, 7, 8
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `pangloss/data/matrix.py:97-143` — Current `build_matrix()` speaker lookup chain. Lines 115-118 load mappings, lines 131-143 perform the lookup.
  - `pangloss/data/speakers.py:274-329` — `load_speaker_counts()` function. Lines 311-316 show the mixed-key storage: `result[asjp_id] = speaker_count` if mapping exists, else `result[iso_code] = speaker_count`.
  - `pangloss/data/speakers.py:218-243` — `get_all_asjp_iso_mappings()` returns `asjp_id → iso_code` dict.
  - `pangloss/data/speakers.py:186-215` — `load_asjp_languages()` returns `iso_code → first_asjp_id`.

  **WHY Each Reference Matters**:
  - `matrix.py:97-143`: This is the code to modify. The fix replaces the fragile 3-hop lookup with a direct ISO-based lookup.
  - `speakers.py:274-329`: Explains WHY the mixed keyspace exists — `asjp_id` when ISO→ASJP mapping exists, `iso_code` otherwise.
  - `speakers.py:218-243`: This helper is already imported and used — the fix builds on it.
  - `speakers.py:186-215`: Shows the `iso_code → first_asjp_id` mapping which currently creates ambiguity.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Fewer languages have speakers=0 after canonicalization
    Tool: Bash
    Preconditions: Delete data/speakers.json to force regeneration, then rebuild
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
asjp = load_asjp('data/asjp')
speakers = load_speaker_counts()
matrix = build_matrix(asjp, speakers)
water = matrix.get('*water')
if water:
    zero_count = sum(1 for e in water.entries if e.speaker_count == 0)
    total = len(water.entries)
    print(f'Water: {zero_count}/{total} entries have speakers=0')
" 2>&1`
      3. Assert: The zero_count should be lower than before (baseline: many entries had speakers=0)
    Expected Result: More languages successfully mapped to speaker counts
    Failure Indicators: Same or higher zero_count than baseline
    Evidence: .sisyphus/evidence/task-4-speaker-mapping.txt

  Scenario: No KeyError or lookup failures during matrix build
    Tool: Bash
    Steps:
      1. Run: `python -m pangloss generate --verbose 2>&1`
      2. Assert: exit code is 0
      3. Assert: stderr "unmapped languages" count is lower than baseline
    Expected Result: Pipeline completes with fewer unmapped languages
    Evidence: .sisyphus/evidence/task-4-pipeline-clean.txt
  ```

  **Commit**: YES (groups with T5)
  - Message: `fix(matrix): canonicalize speaker lookup to ISO keys`
  - Files: `pangloss/data/matrix.py`

- [ ] 5. De-duplicate total_speakers in matrix.py + pass language_to_speakers

  **What to do**:
  - In `pangloss/data/matrix.py` lines 164-165: `total_speakers = sum(entry.speaker_count for entry in entries)` inflates the count because multiple ASJP variants of the same language (e.g., `MANDARIN_BEIJING`, `MANDARIN_SHANGHAI`) share the same ISO code and thus the same speaker count.
  - Fix: After Task 4's ISO-canonical lookup is in place, compute `total_speakers` by de-duplicating via ISO code:
    ```python
    # Build ISO → speaker_count for this concept (de-duplicated)
    iso_speakers_seen = {}
    for entry in entries:
        iso_code = asjp_to_iso.get(entry.language_id)
        if iso_code and iso_code not in iso_speakers_seen:
            iso_speakers_seen[iso_code] = entry.speaker_count
        elif not iso_code and entry.speaker_count > 0:
            iso_speakers_seen[entry.language_id] = entry.speaker_count
    total_speakers = sum(iso_speakers_seen.values())
    ```
  - Also add a `language_to_speakers: Dict[str, int]` field to `ConceptEntry` dataclass (maps `language_id → speaker_count` for each entry). This is needed by Task 8 (selector fix).
  - Add a `total_unique_speakers: int` field to `ConceptEntry` that stores the de-duplicated total.

  **Must NOT do**:
  - Do NOT remove the existing `total_speakers` field — keep it for backward compatibility, or rename to `total_speakers_raw` if clearer
  - Do NOT change `MatrixEntry` dataclass

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Touches dataclass structure, impacts downstream consumers
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 4)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 6, 7, 8, 13
  - **Blocked By**: Tasks 3, 4

  **References**:

  **Pattern References**:
  - `pangloss/data/matrix.py:42-61` — `ConceptEntry` dataclass. Add `language_to_speakers: Dict[str, int]` and `total_unique_speakers: int` fields.
  - `pangloss/data/matrix.py:122-179` — Main loop in `build_matrix()`. Lines 164-165 compute `total_speakers`. The fix de-duplicates by ISO code.
  - `pangloss/algo/generator.py:64` — `total_world_speakers = sum(e.speaker_count for e in entries)` — downstream consumer that should use `ConceptEntry.total_unique_speakers` instead.
  - `pangloss/algo/selector.py:93-96` — Infers `total_speakers` from `coverage_pct` — fragile. Task 8 will fix this to use `language_to_speakers` directly.

  **WHY Each Reference Matters**:
  - `matrix.py:42-61`: Dataclass to extend with new fields.
  - `matrix.py:122-179`: Main code to modify — the de-duplication logic goes here.
  - `generator.py:64`: Must be updated to use de-duplicated total (otherwise coverage_pct is wrong).
  - `selector.py:93-96`: Shows why `language_to_speakers` dict is needed downstream.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: total_unique_speakers is less than total_speakers
    Tool: Bash
    Preconditions: Pipeline dependencies available
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
asjp = load_asjp('data/asjp')
speakers = load_speaker_counts()
matrix = build_matrix(asjp, speakers)
water = matrix.get('*water')
if water:
    print(f'total_speakers (raw): {water.total_speakers:,}')
    print(f'total_unique_speakers: {water.total_unique_speakers:,}')
    print(f'language_to_speakers entries: {len(water.language_to_speakers)}')
    assert water.total_unique_speakers <= water.total_speakers, 'De-dup should be <= raw'
    assert len(water.language_to_speakers) == len(water.entries), 'Every entry should have a speaker mapping'
" 2>&1`
      3. Assert: `total_unique_speakers <= total_speakers`
      4. Assert: `language_to_speakers` has an entry for every MatrixEntry
    Expected Result: De-duplicated speaker count is lower, per-language dict is populated
    Failure Indicators: AssertionError, KeyError
    Evidence: .sisyphus/evidence/task-5-dedup-speakers.txt
  ```

  **Commit**: YES (groups with T4)
  - Message: `feat(matrix): de-duplicate total_speakers by ISO code, add language_to_speakers`
  - Files: `pangloss/data/matrix.py`

- [x] 6. Fix convergence scoring formula

  **What to do**:
  - In `pangloss/algo/convergence.py` line 111: Change `score = float(depth * speaker_count)` to `score = float(depth * math.log1p(speaker_count))`.
  - Add `import math` at top of file.
  - This dampens mega-language overweighting. `log1p` handles `speaker_count=0` safely (returns 0.0).
  - In lines 139-143: Replace asymmetric distinctness filter with Jaccard-based threshold:
    ```python
    # OLD: overlap / min_len > 0.2 (asymmetric, rejects small diverse clusters)
    # NEW: Jaccard similarity threshold
    union_len = len(candidate.languages | selected.languages)
    if union_len > 0:
        jaccard = len(candidate.languages & selected.languages) / union_len
        if jaccard > 0.5:
            is_distinct = False
            break
    ```
  - Make the distinctness threshold (0.5) and k value configurable by adding them as parameters to `find_convergence_points()`.

  **Must NOT do**:
  - Do NOT change the ConvergencePoint dataclass
  - Do NOT change the split pair generation logic (lines 67-79) — that's correct
  - Do NOT change the trie node lookup logic (lines 84-91)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Algorithm change with correctness implications, needs careful formula replacement
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 7, after Task 5)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 8, 11, 13
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `pangloss/algo/convergence.py:1-15` — Imports section. Add `import math`.
  - `pangloss/algo/convergence.py:39-44` — Function signature. Add `distinctness_threshold: float = 0.5` parameter.
  - `pangloss/algo/convergence.py:111` — Score formula: `score = float(depth * speaker_count)`. Replace with `float(depth * math.log1p(speaker_count))`.
  - `pangloss/algo/convergence.py:137-150` — Distinctness filtering loop. Replace overlap/min_len with Jaccard.
  - `pangloss/cli.py:157-158` — Caller: `find_convergence_points(prefix_trie, suffix_trie, concept_entry.entries, k=20)`. Must update to pass k from CLI arg.

  **WHY Each Reference Matters**:
  - Lines 111, 137-150: The two specific code blocks to change.
  - Lines 39-44: Function signature to extend with new parameters.
  - `cli.py:157-158`: The caller that passes `k=20` — must be updated in Task 13 to use CLI arg.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Convergence points are more diverse (not dominated by mega-languages)
    Tool: Bash
    Preconditions: Pipeline runs with new scoring
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
asjp = load_asjp('data/asjp')
speakers = load_speaker_counts()
matrix = build_matrix(asjp, speakers)
water = matrix.get('*water')
pt = build_prefix_trie(water.entries)
st = build_suffix_trie(water.entries)
points = find_convergence_points(pt, st, water.entries, k=20)
print(f'Found {len(points)} convergence points for water')
for i, p in enumerate(points[:5]):
    print(f'  {i+1}. prefix={p.prefix_phonemes}, suffix={p.suffix_phonemes}, langs={len(p.languages)}, speakers={p.speaker_count:,}, score={p.score:.1f}')
" 2>&1`
      3. Assert: More than 5 convergence points found (previously, aggressive filtering reduced count)
      4. Assert: Points show diverse language sets, not all dominated by same mega-language cluster
    Expected Result: More diverse convergence points with dampened mega-language bias
    Failure Indicators: Only 1-3 points found, or all points have nearly identical language sets
    Evidence: .sisyphus/evidence/task-6-convergence-diversity.txt

  Scenario: log1p handles zero speakers safely
    Tool: Bash
    Steps:
      1. Run: `python -c "import math; print(math.log1p(0))"`
      2. Assert: output is "0.0" (no error)
    Expected Result: Zero speakers don't cause math errors
    Evidence: .sisyphus/evidence/task-6-log1p-zero.txt
  ```

  **Commit**: YES (groups with T7, T8)
  - Message: `feat(convergence): use log-dampened scoring, Jaccard distinctness filter`
  - Files: `pangloss/algo/convergence.py`

- [x] 7. Fix generator scoring formula

  **What to do**:
  - In `pangloss/algo/generator.py` lines 52-56: Replace the scoring function that REWARDS length with one that PENALIZES length:
    ```python
    def calculate_score(speakers: int, prefix_len: int, suffix_len: int) -> float:
        length = prefix_len + suffix_len
        return speakers / (1.0 + 0.5 * length)
    ```
  - This favors short, high-coverage forms over long forms that happen to match more languages.
  - In `pangloss/algo/generator.py` line 64: Change `total_world_speakers = sum(e.speaker_count for e in entries)` to use the de-duplicated total. Since `entries` is a list of `MatrixEntry`, and after Task 5 we have `ConceptEntry.total_unique_speakers`, we need to pass this value in. Add `total_speakers: int` parameter to `generate_word()`.
  - Add `max_word_length: int = 8` parameter to `generate_word()` to make the length cap configurable (currently hardcoded at line 96 and 133 as `8`).

  **Must NOT do**:
  - Do NOT change the greedy extension loop structure (left extension then right extension) — just change what score function it uses
  - Do NOT change `SyntheticWord` dataclass fields
  - Do NOT change `get_transliteration()` — that's correct

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Algorithm change affecting word quality and coverage
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6, after Task 5)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 8, 11, 13
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `pangloss/algo/generator.py:52-56` — `calculate_score()` function. The current formula: `speakers * ((prefix_len * 2) + suffix_len)`. Replace entirely.
  - `pangloss/algo/generator.py:58-63` — `generate_word()` signature. Add `total_speakers: int` and `max_word_length: int = 8` parameters.
  - `pangloss/algo/generator.py:64` — `total_world_speakers = sum(e.speaker_count for e in entries)`. Replace with passed-in `total_speakers` parameter.
  - `pangloss/algo/generator.py:96,133` — `while len(current_prefix) + len(current_suffix) < 8` — replace `8` with `max_word_length`.
  - `pangloss/cli.py:162-164` — Caller: `generate_word(p, prefix_trie, suffix_trie, concept_entry.entries)`. Must update to pass `total_speakers` and `max_word_length`.

  **WHY Each Reference Matters**:
  - Lines 52-56: The formula to replace — the core algorithmic change.
  - Line 64: Must use de-duplicated total from ConceptEntry for correct coverage_pct.
  - Lines 96, 133: Hardcoded length cap to make configurable.
  - `cli.py:162-164`: Caller to update with new parameters.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Generated words favor short forms
    Tool: Bash
    Preconditions: After scoring fix applied
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
from pangloss.algo.generator import generate_word
asjp = load_asjp('data/asjp')
speakers = load_speaker_counts()
matrix = build_matrix(asjp, speakers)
water = matrix.get('*water')
pt = build_prefix_trie(water.entries)
st = build_suffix_trie(water.entries)
points = find_convergence_points(pt, st, water.entries, k=20)
for i, p in enumerate(points[:5]):
    word = generate_word(p, pt, st, water.entries, total_speakers=water.total_unique_speakers)
    print(f'  {i+1}. form={word.form}, phonemes={len(word.phonemes)}, coverage={word.coverage_pct:.1f}%, speakers={word.speaker_count:,}')
" 2>&1`
      3. Assert: Average phoneme count per word is ≤ 5 (short forms preferred)
      4. Assert: coverage_pct values are reasonable (not all 0.0 or > 100)
    Expected Result: Shorter, high-coverage words generated
    Failure Indicators: Words consistently at max length (8 phonemes), or 0% coverage
    Evidence: .sisyphus/evidence/task-7-short-forms.txt
  ```

  **Commit**: YES (groups with T6, T8)
  - Message: `feat(generator): penalize length instead of rewarding, use de-duped total_speakers`
  - Files: `pangloss/algo/generator.py`

- [ ] 8. Fix selector with per-language speaker weights

  **What to do**:
  - In `pangloss/algo/selector.py`: Replace the proportional speaker estimate with exact per-language marginal gain computation.
  - Add `language_to_speakers: Dict[str, int] = None` and `total_speakers: int = 0` parameters to `select_synonyms()`.
  - Replace lines 93-99 (backward inference of total_speakers from coverage_pct) with direct use of `total_speakers` parameter.
  - Replace lines 128-134 (proportional estimate) with exact computation:
    ```python
    # For each candidate, compute exact marginal speaker gain
    new_languages = candidate.covered_languages & uncovered_languages
    if language_to_speakers:
        estimated_speakers = sum(language_to_speakers.get(lang, 0) for lang in new_languages)
    else:
        # Fallback to proportional estimate
        language_ratio = len(new_languages) / len(candidate.covered_languages) if candidate.covered_languages else 0
        estimated_speakers = int(candidate.speaker_count * language_ratio)
    ```
  - Update `pangloss/cli.py` line 168 to pass `language_to_speakers` and `total_speakers` from `concept_entry`:
    ```python
    selected = select_synonyms(
        candidates, coverage_threshold,
        language_to_speakers=concept_entry.language_to_speakers,
        total_speakers=concept_entry.total_unique_speakers
    )
    ```

  **Must NOT do**:
  - Do NOT remove the proportional fallback — keep it for backward compatibility when `language_to_speakers` is None
  - Do NOT change the greedy selection strategy (weighted set cover) — just improve the weight estimation

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires careful integration of data flows from matrix → convergence → generator → selector
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T5, T6, T7)
  - **Parallel Group**: Wave 2 (last task in wave)
  - **Blocks**: Tasks 9, 13
  - **Blocked By**: Tasks 5, 6, 7

  **References**:

  **Pattern References**:
  - `pangloss/algo/selector.py:11-13` — `select_synonyms()` signature. Add `language_to_speakers` and `total_speakers` parameters.
  - `pangloss/algo/selector.py:93-99` — Backward inference of total_speakers from coverage_pct. Replace with direct parameter.
  - `pangloss/algo/selector.py:123-134` — Proportional speaker estimate loop. Replace with exact marginal gain.
  - `pangloss/data/matrix.py:42-61` — `ConceptEntry` dataclass (after Task 5 adds `language_to_speakers` and `total_unique_speakers`).
  - `pangloss/cli.py:168` — `selected = select_synonyms(candidates, coverage_threshold)`. Update call to pass new parameters.

  **WHY Each Reference Matters**:
  - `selector.py:11-13`: Function signature to extend.
  - `selector.py:93-99`: The fragile backward-inference code to replace.
  - `selector.py:123-134`: The proportional estimate code to replace with exact computation.
  - `matrix.py:42-61`: Shows the new fields available after Task 5.
  - `cli.py:168`: The caller that connects matrix data to selector.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Selector uses exact marginal gains
    Tool: Bash
    Preconditions: Tasks 4-7 complete
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate && python -m pangloss generate --verbose 2>&1`
      2. Run: `python -c "
import json
d = json.load(open('output/summary.json'))
print(f'Average coverage: {d[\"avg_coverage_pct\"]:.1f}%')
print(f'Min coverage: {d[\"min_coverage_pct\"]:.1f}%')
print(f'Max coverage: {d[\"max_coverage_pct\"]:.1f}%')
# Baseline was 36.25% average
assert d['avg_coverage_pct'] > 36.25, f'Coverage should improve from 36.25% baseline, got {d[\"avg_coverage_pct\"]}'
" 2>&1`
      3. Assert: `avg_coverage_pct > 36.25` (improvement over baseline)
      4. Assert: no concept has 0 synonyms
    Expected Result: Measurable coverage improvement from the algorithm overhaul
    Failure Indicators: Coverage same or worse than 36.25% baseline
    Evidence: .sisyphus/evidence/task-8-coverage-improvement.txt

  Scenario: No concept has zero synonyms
    Tool: Bash
    Steps:
      1. Run: `python -c "
import json
d = json.load(open('output/dictionary.json'))
zero_syn = [c['concept'] for c in d['concepts'] if c['synonym_count'] == 0]
print(f'Concepts with 0 synonyms: {zero_syn}')
assert len(zero_syn) == 0, f'Some concepts have 0 synonyms: {zero_syn}'
" 2>&1`
      2. Assert: empty list (no zero-synonym concepts)
    Expected Result: Every concept gets at least one synonym
    Evidence: .sisyphus/evidence/task-8-no-zero-synonyms.txt
  ```

  **Commit**: YES (groups with T6, T7)
  - Message: `feat(selector): use exact per-language marginal gains instead of proportional estimate`
  - Files: `pangloss/algo/selector.py`, `pangloss/cli.py`

- [ ] 9. Add collision detection module + CLI integration

  **What to do**:
  - Create new file `pangloss/algo/collisions.py` with a `detect_collisions()` function.
  - **Exact collisions**: Build `normalized_form → list[(concept_name, SyntheticWord)]` map across ALL concepts. Any key with >1 entry from DIFFERENT concepts = cross-concept collision.
  - **Near-collisions**: Use `difflib.SequenceMatcher` on IPA strings. For all cross-concept word pairs, compute similarity. Threshold ≥ 0.85 = near-collision.
  - **Within-concept collisions**: Check if any two synonyms within the same concept have identical `form` or IPA similarity ≥ 0.85.
  - Check BOTH `form` (transliteration) and `ipa` fields separately.
  - Return structured collision report:
    ```python
    {
        "exact_collisions": [
            {"form": "ak", "concepts": ["*water", "*fire"], "type": "transliteration"},
            ...
        ],
        "near_collisions": [
            {"pair": [{"concept": "*water", "form": "ak", "ipa": "/ak/"}, {...}], "similarity": 0.87, "type": "ipa"},
            ...
        ],
        "within_concept_collisions": [
            {"concept": "*water", "forms": ["ak", "aku"], "similarity": 0.90},
            ...
        ]
    }
    ```
  - Integrate into `pangloss/output/dictionary.py`: Add collision report as top-level `"collisions"` key in dictionary output.
  - Call from CLI after synonym selection in `pangloss/cli.py`.

  **Must NOT do**:
  - Do NOT auto-resolve collisions (remove or replace words) — report only
  - Do NOT add external dependencies — use `difflib.SequenceMatcher` from stdlib
  - Do NOT change the dictionary structure for existing fields — only ADD the new `"collisions"` key

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: New module creation with integration into existing pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Task 8

  **References**:

  **Pattern References**:
  - `pangloss/algo/selector.py:1-10` — Existing algo module structure pattern. Follow same style (docstring, imports, type hints).
  - `pangloss/algo/generator.py:6-14` — `SyntheticWord` dataclass fields: `form`, `ipa`, `covered_languages`.
  - `pangloss/output/dictionary.py:22-99` — `format_dictionary()` function. The collision report should be added to the returned dict alongside `"concepts"`.
  - `pangloss/cli.py:176-177` — `results[concept_name] = selected`. After this loop, `results` has all concepts → call `detect_collisions(results)`.

  **External References**:
  - Python stdlib: `difflib.SequenceMatcher` — `ratio()` method returns similarity between 0.0 and 1.0.

  **WHY Each Reference Matters**:
  - `selector.py:1-10`: Follow this module's code style for the new file.
  - `generator.py:6-14`: Shows the dataclass fields available for comparison.
  - `dictionary.py:22-99`: Integration point — add collision data to output dict.
  - `cli.py:176-177`: Where to call collision detection in the pipeline.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Collision report appears in dictionary output
    Tool: Bash
    Preconditions: Full pipeline with collision detection
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate && python -m pangloss generate --verbose 2>&1`
      2. Run: `python -c "
import json
d = json.load(open('output/dictionary.json'))
assert 'collisions' in d, 'Missing collisions key in dictionary output'
c = d['collisions']
print(f'Exact collisions: {len(c.get(\"exact_collisions\", []))}')
print(f'Near collisions: {len(c.get(\"near_collisions\", []))}')
print(f'Within-concept: {len(c.get(\"within_concept_collisions\", []))}')
# Print first few for inspection
for coll in c.get('exact_collisions', [])[:3]:
    print(f'  EXACT: form={coll[\"form\"]}, concepts={coll[\"concepts\"]}')
for coll in c.get('near_collisions', [])[:3]:
    print(f'  NEAR: similarity={coll[\"similarity\"]:.2f}, pair={[p[\"form\"] for p in coll[\"pair\"]]}')
" 2>&1`
      3. Assert: `collisions` key exists in output
      4. Assert: each sub-list is a valid list (may be empty if no collisions found)
    Expected Result: Collision report is structured, present, and parseable
    Failure Indicators: KeyError on 'collisions', malformed JSON
    Evidence: .sisyphus/evidence/task-9-collision-report.txt

  Scenario: Near-collision detection catches similar words
    Tool: Bash
    Steps:
      1. Run: `python -c "
from difflib import SequenceMatcher
# Verify the detection mechanism works
s = SequenceMatcher(None, '/ak/', '/aku/')
print(f'Similarity ak vs aku: {s.ratio():.3f}')
s2 = SequenceMatcher(None, '/water/', '/fire/')
print(f'Similarity water vs fire: {s2.ratio():.3f}')
assert s.ratio() > 0.5, 'Similar words should have high ratio'
assert s2.ratio() < 0.5, 'Different words should have low ratio'
" 2>&1`
      2. Assert: Similar IPA strings produce high similarity, different ones produce low
    Expected Result: SequenceMatcher correctly distinguishes similar vs different
    Evidence: .sisyphus/evidence/task-9-sequencematcher-test.txt
  ```

  **Commit**: YES
  - Message: `feat(algo): add collision detection for cross-concept and within-concept conflicts`
  - Files: `pangloss/algo/collisions.py` (new), `pangloss/output/dictionary.py`, `pangloss/cli.py`

- [ ] 10. Add articulatory feature groups to phonemes.py

  **What to do**:
  - In `pangloss/data/phonemes.py`: Add a phoneme feature system for fuzzy matching.
  - Define articulatory feature groups as a dict mapping each phoneme to its feature vector:
    ```python
    PHONEME_FEATURES = {
        # Stops: (place, manner=stop, voicing)
        "p": ("bilabial", "stop", "voiceless"),
        "b": ("bilabial", "stop", "voiced"),
        "t": ("alveolar", "stop", "voiceless"),
        "d": ("alveolar", "stop", "voiced"),
        "k": ("velar", "stop", "voiceless"),
        "ɡ": ("velar", "stop", "voiced"),
        # Fricatives
        "f": ("labiodental", "fricative", "voiceless"),
        "v": ("labiodental", "fricative", "voiced"),
        "s": ("alveolar", "fricative", "voiceless"),
        "z": ("alveolar", "fricative", "voiced"),
        "ʃ": ("postalveolar", "fricative", "voiceless"),
        "ʂ": ("retroflex", "fricative", "voiceless"),
        "x": ("velar", "fricative", "voiceless"),
        "h": ("glottal", "fricative", "voiceless"),
        # Nasals
        "m": ("bilabial", "nasal", "voiced"),
        "n": ("alveolar", "nasal", "voiced"),
        "ŋ": ("velar", "nasal", "voiced"),
        "ɲ": ("palatal", "nasal", "voiced"),
        # Approximants / Liquids
        "l": ("alveolar", "lateral", "voiced"),
        "r": ("alveolar", "trill", "voiced"),
        "ɾ": ("alveolar", "tap", "voiced"),
        "ɹ": ("alveolar", "approximant", "voiced"),
        "j": ("palatal", "approximant", "voiced"),
        "w": ("labial-velar", "approximant", "voiced"),
        # Vowels (height, backness, rounding)
        "a": ("open", "central", "unrounded"),
        "e": ("mid", "front", "unrounded"),
        "i": ("close", "front", "unrounded"),
        "o": ("mid", "back", "rounded"),
        "u": ("close", "back", "rounded"),
        "ə": ("mid", "central", "unrounded"),
        # ... etc. Cover the most common IPA symbols found in ASJP data
    }
    ```
  - Add a `phoneme_distance(p1: str, p2: str) -> float` function:
    - Returns 0.0 if identical
    - Returns 0.0-0.3 if same manner and differ only in voicing (e.g., /t/ ↔ /d/)
    - Returns 0.0-0.5 if same manner and differ only in place (e.g., /t/ ↔ /k/)
    - Returns 1.0 if unknown or completely different (different manner class, or vowel vs consonant)
  - Handle multi-character phonemes (`tʃ`, `dʒ`, `aː`) by looking up the base character.
  - Add a `fuzzy_phoneme_match(p1: str, p2: str, threshold: float = 0.5) -> bool` convenience function that returns True if distance < threshold.

  **Must NOT do**:
  - Do NOT modify existing normalization functions — this is additive
  - Do NOT add external dependencies — all feature data is hardcoded
  - Do NOT attempt to cover ALL IPA symbols — cover the most common 40-50 found in ASJP data
  - Do NOT create a dynamic feature extraction system — hardcode the feature dict

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires phonetics domain knowledge, but implementation is straightforward dict + function
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 11
  - **Blocked By**: None (phoneme features are independent of scoring changes)

  **References**:

  **Pattern References**:
  - `pangloss/data/phonemes.py:43-48` — `IPA_VARIANT_MAP` dict. Follow this pattern for the feature dict.
  - `pangloss/data/phonemes.py:51-107` — `normalize_phoneme()` function. The feature lookup should handle the same edge cases (combining characters, multi-char phonemes).
  - `pangloss/algo/convergence.py:65` — `lang_speakers = {entry.language_id: entry.speaker_count for entry in entries}` — shows how the convergence module uses phoneme data.

  **WHY Each Reference Matters**:
  - `phonemes.py:43-48`: Existing dict pattern to follow for consistency.
  - `phonemes.py:51-107`: Shows edge cases in phoneme handling that feature lookup must also handle.
  - `convergence.py:65`: Context for how features will be used downstream in Task 11.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Phoneme distance produces correct results for known pairs
    Tool: Bash
    Preconditions: Feature dict and distance function added
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.phonemes import phoneme_distance, fuzzy_phoneme_match
# Same phoneme
assert phoneme_distance('t', 't') == 0.0, 'Same phoneme should be 0.0'
# Voicing difference only
d_td = phoneme_distance('t', 'd')
print(f't vs d: {d_td:.2f}')
assert 0.0 < d_td <= 0.3, f'Voicing pair should be close: {d_td}'
# Same manner, different place
d_tk = phoneme_distance('t', 'k')
print(f't vs k: {d_tk:.2f}')
assert 0.0 < d_tk <= 0.5, f'Same manner/different place should be moderate: {d_tk}'
# Completely different
d_av = phoneme_distance('a', 't')
print(f'a vs t: {d_av:.2f}')
assert d_av >= 0.8, f'Vowel vs consonant should be distant: {d_av}'
# Fuzzy match convenience
assert fuzzy_phoneme_match('t', 'd'), 't and d should fuzzy match'
assert not fuzzy_phoneme_match('a', 't'), 'a and t should not fuzzy match'
print('All phoneme distance checks passed!')
" 2>&1`
      3. Assert: All assertions pass
    Expected Result: Distance function correctly captures articulatory similarity
    Failure Indicators: AssertionError on any check
    Evidence: .sisyphus/evidence/task-10-phoneme-distance.txt

  Scenario: Multi-character phonemes handled
    Tool: Bash
    Steps:
      1. Run: `python -c "
from pangloss.data.phonemes import phoneme_distance
# Multi-char phoneme
d = phoneme_distance('tʃ', 'dʒ')
print(f'tʃ vs dʒ: {d:.2f}')
# Length-marked phoneme
d2 = phoneme_distance('aː', 'a')
print(f'aː vs a: {d2:.2f}')
print('Multi-char phoneme checks passed!')
" 2>&1`
      2. Assert: no errors, reasonable distance values
    Expected Result: Multi-character and length-marked phonemes handled gracefully
    Evidence: .sisyphus/evidence/task-10-multichar.txt
  ```

  **Commit**: YES
  - Message: `feat(phonemes): add articulatory feature groups and phoneme distance function`
  - Files: `pangloss/data/phonemes.py`

- [ ] 11. Integrate fuzzy matching into convergence + generator

  **What to do**:
  - In `pangloss/algo/convergence.py`: Modify the language intersection computation to allow near-matches.
  - Currently (lines 89-93): intersection requires EXACT phoneme match in both prefix and suffix tries. With fuzzy matching, a language whose prefix differs by only a close phoneme (e.g., /t/ vs /d/) should be counted as a partial match.
  - Implementation approach:
    1. For each split pair, compute exact intersection as before.
    2. Then check languages NOT in the exact intersection: if their phoneme sequence at this split point differs by at most 1 fuzzy-matchable phoneme (using `phoneme_distance` from Task 10), add them to a "fuzzy_languages" set with a discount factor (e.g., 0.5x weight).
    3. Combine: `effective_speakers = exact_speakers + 0.5 * fuzzy_speakers`.
    4. Add `fuzzy: bool = False` parameter to `find_convergence_points()` to enable/disable.
  - In `pangloss/algo/generator.py`: Similarly extend the greedy extension to consider fuzzy matches when computing intersection.
    - Add `fuzzy: bool = False` parameter to `generate_word()`.
    - In `get_intersection()` helper (lines 72-84), optionally include fuzzy-matched languages.
  - Keep it simple: fuzzy matching should add coverage, not replace exact matching.

  **Must NOT do**:
  - Do NOT make fuzzy matching the default — it must be opt-in via parameter
  - Do NOT change the trie structure — fuzzy matching happens at the scoring/intersection layer
  - Do NOT use O(n³) or worse algorithms — keep the fuzzy check lightweight
  - Do NOT modify the `ConvergencePoint` or `SyntheticWord` dataclasses — store fuzzy info in reasoning text

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex algorithmic change touching core scoring logic in two modules, requires careful integration with exact matching
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T6, T7, T10)
  - **Parallel Group**: Wave 3 (after T6, T7 scoring changes, and T10 feature groups)
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 6, 7, 10

  **References**:

  **Pattern References**:
  - `pangloss/algo/convergence.py:64-125` — Main scoring loop. Lines 89-93 compute exact intersection. Fuzzy matching extends this intersection.
  - `pangloss/algo/convergence.py:99` — `speaker_count = sum(lang_speakers.get(lang, 0) for lang in intersect_langs)`. Fuzzy languages get discounted weight.
  - `pangloss/algo/generator.py:72-84` — `get_intersection()` helper. This is the function to extend with fuzzy matching.
  - `pangloss/data/phonemes.py` (after Task 10) — `phoneme_distance()` and `fuzzy_phoneme_match()` functions.
  - `pangloss/data/matrix.py:20-39` — `MatrixEntry` has `phonemes: List[str]` — the phoneme sequences to compare.

  **WHY Each Reference Matters**:
  - `convergence.py:64-125`: The exact code section to extend with fuzzy intersection.
  - `convergence.py:99`: Where discounted fuzzy speakers are added.
  - `generator.py:72-84`: The intersection helper to extend in parallel.
  - `phonemes.py`: The distance function this task depends on.
  - `matrix.py:20-39`: Shows the phoneme data format available on entries.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Fuzzy matching increases coverage when enabled
    Tool: Bash
    Preconditions: Tasks 6, 7, 10 complete
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `python -c "
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
asjp = load_asjp('data/asjp')
speakers = load_speaker_counts()
matrix = build_matrix(asjp, speakers)
water = matrix.get('*water')
pt = build_prefix_trie(water.entries)
st = build_suffix_trie(water.entries)
# Without fuzzy
points_exact = find_convergence_points(pt, st, water.entries, k=20, fuzzy=False)
# With fuzzy
points_fuzzy = find_convergence_points(pt, st, water.entries, k=20, fuzzy=True)
exact_max_langs = max(len(p.languages) for p in points_exact) if points_exact else 0
fuzzy_max_langs = max(len(p.languages) for p in points_fuzzy) if points_fuzzy else 0
print(f'Exact: {len(points_exact)} points, max languages in best: {exact_max_langs}')
print(f'Fuzzy: {len(points_fuzzy)} points, max languages in best: {fuzzy_max_langs}')
# Fuzzy should generally find >= exact number of points
assert len(points_fuzzy) >= len(points_exact), 'Fuzzy should find at least as many points'
" 2>&1`
      3. Assert: Fuzzy finds >= exact number of convergence points
      4. Assert: Best fuzzy point covers >= languages as best exact point
    Expected Result: Fuzzy matching adds coverage without reducing exact match quality
    Failure Indicators: Fuzzy results worse than exact, or errors
    Evidence: .sisyphus/evidence/task-11-fuzzy-convergence.txt

  Scenario: Fuzzy matching disabled by default (backward compatible)
    Tool: Bash
    Steps:
      1. Run: `python -c "
import inspect
from pangloss.algo.convergence import find_convergence_points
sig = inspect.signature(find_convergence_points)
fuzzy_param = sig.parameters.get('fuzzy')
assert fuzzy_param is not None, 'fuzzy parameter should exist'
assert fuzzy_param.default == False, f'fuzzy should default to False, got {fuzzy_param.default}'
print('Fuzzy parameter defaults to False (backward compatible)')
" 2>&1`
      2. Assert: `fuzzy` parameter exists and defaults to False
    Expected Result: Backward compatibility preserved
    Evidence: .sisyphus/evidence/task-11-fuzzy-default.txt
  ```

  **Commit**: YES
  - Message: `feat(algo): integrate fuzzy phoneme matching into convergence and generator`
  - Files: `pangloss/algo/convergence.py`, `pangloss/algo/generator.py`

- [ ] 12. Add matrix caching with hash-based invalidation

  **What to do**:
  - In `pangloss/data/matrix.py`: Add caching to `build_matrix()` to avoid re-processing ASJP data on every run.
  - Cache strategy:
    1. Compute SHA256 hash of the 3 input CSV files (`forms.csv`, `parameters.csv`, `languages.csv`) using file size + mtime (NOT full content — files are 100MB+, hashing full content would be slower than rebuilding).
    2. Also hash `data/speakers.json` mtime (speaker cache).
    3. Store cache as JSON in `data/matrix_cache.json` with structure:
       ```json
       {
         "meta": {
           "forms_mtime": 1234567890.0,
           "forms_size": 104857600,
           "parameters_mtime": 1234567891.0,
           "parameters_size": 4096,
           "languages_mtime": 1234567892.0,
           "languages_size": 524288,
           "speakers_mtime": 1234567893.0,
           "version": "2"
         },
         "matrix": { ... serialized ConceptEntry data ... }
       }
       ```
    4. On load: check if cache exists, compare meta against current file stats. If match → deserialize and return. If mismatch → rebuild, cache, return.
  - For serialization: Since `ConceptEntry` contains sets and dataclasses, serialize to JSON-compatible format (sets → sorted lists, dataclasses → dicts). Deserialize back on load.
  - Add `--no-cache` flag to CLI to force rebuild.

  **Must NOT do**:
  - Do NOT use `pickle` — security risk (arbitrary code execution on `pickle.load`)
  - Do NOT hash full file contents — too slow for 100MB+ files
  - Do NOT add cache versioning/migration — simple invalidate-and-rebuild
  - Do NOT cache tries or convergence points — only the matrix

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires careful serialization/deserialization of dataclass structures + file stat handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10, 11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `pangloss/data/matrix.py:64-186` — `build_matrix()` function. Cache loading goes at the start, cache saving at the end.
  - `pangloss/data/matrix.py:20-61` — `MatrixEntry` and `ConceptEntry` dataclasses. These need JSON serialization helpers.
  - `pangloss/data/speakers.py:298-303` — Existing cache pattern in `load_speaker_counts()`. Follow same style: check cache → load or rebuild.
  - `pangloss/cli.py:70` — Where to add `--no-cache` option to `generate` command.

  **WHY Each Reference Matters**:
  - `matrix.py:64-186`: The function to wrap with caching — entry and exit points for cache logic.
  - `matrix.py:20-61`: Dataclasses to serialize — need to handle `Set[str]` → `List[str]` conversion.
  - `speakers.py:298-303`: Shows the caching pattern already used in this codebase.
  - `cli.py:70`: CLI integration point for `--no-cache` flag.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Cache is created on first run
    Tool: Bash
    Preconditions: No cache exists
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `rm -f data/matrix_cache.json`
      3. Run: `python -m pangloss generate --verbose 2>&1`
      4. Assert: `data/matrix_cache.json` exists
      5. Run: `python -c "import json; d=json.load(open('data/matrix_cache.json')); print(f'meta keys: {list(d[\"meta\"].keys())}'); print(f'matrix concepts: {len(d[\"matrix\"])}')" 2>&1`
      6. Assert: meta has expected keys, matrix has 40 concepts
    Expected Result: Cache file created with valid structure
    Failure Indicators: File not created, or missing meta/matrix keys
    Evidence: .sisyphus/evidence/task-12-cache-created.txt

  Scenario: Second run uses cache (faster)
    Tool: Bash
    Steps:
      1. Run: `time python -m pangloss generate --verbose 2>&1 | tail -3` (capture time)
      2. Run: `time python -m pangloss generate --verbose 2>&1 | tail -3` (should be faster)
      3. Assert: Second run is measurably faster (stderr should mention cache hit)
    Expected Result: Cache hit on second run, reduced processing time
    Failure Indicators: Same processing time, no cache hit message
    Evidence: .sisyphus/evidence/task-12-cache-hit.txt

  Scenario: --no-cache forces rebuild
    Tool: Bash
    Steps:
      1. Run: `python -m pangloss generate --no-cache --verbose 2>&1`
      2. Assert: exit code 0
      3. Assert: Output shows matrix being rebuilt (not loaded from cache)
    Expected Result: Cache bypassed on demand
    Evidence: .sisyphus/evidence/task-12-no-cache.txt

  Scenario: Stale cache is invalidated
    Tool: Bash
    Steps:
      1. Run: `touch data/asjp/cldf/forms.csv` (change mtime)
      2. Run: `python -m pangloss generate --verbose 2>&1`
      3. Assert: Output shows cache invalidated and matrix rebuilt
      4. Assert: exit code 0
    Expected Result: Changed input file triggers cache invalidation
    Evidence: .sisyphus/evidence/task-12-cache-invalidation.txt
  ```

  **Commit**: YES
  - Message: `feat(matrix): add JSON-based matrix caching with hash invalidation`
  - Files: `pangloss/data/matrix.py`, `pangloss/cli.py`

- [ ] 13. Add CLI tuning knobs + end-to-end pipeline verification

  **What to do**:
  - Add CLI options to `pangloss/cli.py` `generate` command:
    1. `--convergence-k` (default: 20) — Number of convergence points to find per concept
    2. `--max-word-length` (default: 8) — Maximum phoneme count for generated words
    3. `--min-speakers` (default: 0) — Minimum speaker count to include a language in analysis
  - Wire options through the pipeline:
    - Pass `k` to `find_convergence_points()`
    - Pass `max_word_length` to `generate_word()`
    - Filter `concept_entry.entries` by `min_speakers` before trie construction
  - Pass `fuzzy=True` to `find_convergence_points()` and `generate_word()` (enable by default since it's an improvement).
  - Pass `total_speakers=concept_entry.total_unique_speakers` to `generate_word()`.
  - Pass `language_to_speakers=concept_entry.language_to_speakers` and `total_speakers=concept_entry.total_unique_speakers` to `select_synonyms()`.
  - Call `detect_collisions(results)` after the concept processing loop and pass result to `format_dictionary()`.
  - Run full end-to-end pipeline and capture before/after metrics.

  **Must NOT do**:
  - Do NOT add more than the 3 specified CLI options
  - Do NOT restructure the generate command — just add options and wire them through
  - Do NOT change output directory structure

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration task connecting all previous changes, requires testing full pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (final integration)
  - **Parallel Group**: Wave 4 (alone)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 9, 11, 12

  **References**:

  **Pattern References**:
  - `pangloss/cli.py:37-70` — Existing CLI options pattern. Follow same style for new options.
  - `pangloss/cli.py:150-177` — Concept processing loop. This is where all wiring happens:
    - Line 157-158: `find_convergence_points()` call — add `k`, `fuzzy` args
    - Line 162-164: `generate_word()` call — add `total_speakers`, `max_word_length`, `fuzzy` args
    - Line 168: `select_synonyms()` call — add `language_to_speakers`, `total_speakers` args
    - After line 177: Call `detect_collisions(results)` and pass to `format_dictionary()`
  - `pangloss/algo/convergence.py:39-44` — Updated function signature (after Task 6)
  - `pangloss/algo/generator.py:58-63` — Updated function signature (after Task 7)
  - `pangloss/algo/selector.py:11-13` — Updated function signature (after Task 8)
  - `pangloss/algo/collisions.py` — New module (after Task 9)
  - `pangloss/output/dictionary.py:22-25` — `format_dictionary()` needs collision data parameter

  **WHY Each Reference Matters**:
  - `cli.py:37-70`: Pattern for adding new click options.
  - `cli.py:150-177`: The main integration point — every new parameter flows through here.
  - Convergence/generator/selector signatures: Must match the parameters being passed.
  - `collisions.py`: New module to import and call.
  - `dictionary.py:22-25`: Must accept and include collision data in output.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full pipeline runs with all improvements
    Tool: Bash
    Preconditions: All Tasks 1-12 complete
    Steps:
      1. Run: `cd /Users/kusha/Sources/pangloss && source venv/bin/activate`
      2. Run: `rm -rf output/ data/matrix_cache.json`
      3. Run: `python -m pangloss generate --verbose --convergence-k 30 --max-word-length 6 2>&1 | tee /tmp/pangloss-v2-run.txt`
      4. Assert: exit code 0
      5. Assert: 40 concepts processed
      6. Run: `python -c "
import json
s = json.load(open('output/summary.json'))
d = json.load(open('output/dictionary.json'))
print(f'Avg coverage: {s[\"avg_coverage_pct\"]:.1f}%')
print(f'Min coverage: {s[\"min_coverage_pct\"]:.1f}%')
print(f'Max coverage: {s[\"max_coverage_pct\"]:.1f}%')
print(f'Total concepts: {s[\"total_concepts\"]}')
print(f'Collision report: {\"collisions\" in d}')
print(f'Graph files: glob-safe (no *)')
assert s['avg_coverage_pct'] > 36.25, f'Coverage regression: {s[\"avg_coverage_pct\"]}'
assert s['total_concepts'] == 40
assert 'collisions' in d
" 2>&1`
      7. Assert: All assertions pass
    Expected Result: Full pipeline works end-to-end with all improvements
    Failure Indicators: Pipeline error, coverage regression, missing collisions
    Evidence: .sisyphus/evidence/task-13-full-pipeline.txt

  Scenario: CLI tuning knobs work
    Tool: Bash
    Steps:
      1. Run: `python -m pangloss generate --convergence-k 5 --max-word-length 4 --min-speakers 1000000 --concept water --verbose 2>&1`
      2. Assert: exit code 0
      3. Assert: output shows fewer convergence points (k=5 instead of 20)
    Expected Result: Custom parameters accepted and applied
    Failure Indicators: Unknown option error, or default values used instead
    Evidence: .sisyphus/evidence/task-13-cli-knobs.txt

  Scenario: Single concept mode with all improvements
    Tool: Bash
    Steps:
      1. Run: `python -m pangloss generate --concept water --verbose --format yaml 2>&1`
      2. Assert: exit code 0
      3. Assert: `output/dictionary.yaml` exists and contains only water concept
    Expected Result: Single concept mode works with YAML + new features
    Evidence: .sisyphus/evidence/task-13-single-concept.txt

  Scenario: Pipeline metrics comparison (before vs after)
    Tool: Bash
    Steps:
      1. Run: `python -c "
import json
s = json.load(open('output/summary.json'))
baseline = 36.25
improvement = s['avg_coverage_pct'] - baseline
print(f'=== COVERAGE IMPROVEMENT REPORT ===')
print(f'Baseline average coverage: {baseline:.1f}%')
print(f'New average coverage: {s[\"avg_coverage_pct\"]:.1f}%')
print(f'Improvement: +{improvement:.1f}pp')
print(f'Min coverage: {s[\"min_coverage_pct\"]:.1f}%')
print(f'Max coverage: {s[\"max_coverage_pct\"]:.1f}%')
print(f'Avg synonyms: {s[\"avg_synonym_count\"]:.1f}')
print(f'Unique languages: {s[\"total_unique_languages\"]}')
print(f'Unique families: {s[\"total_unique_families\"]}')
" 2>&1`
    Expected Result: Clear improvement metrics documented
    Evidence: .sisyphus/evidence/task-13-metrics-comparison.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): add tuning knobs, wire all v2 improvements through pipeline`
  - Files: `pangloss/cli.py`, `pangloss/output/dictionary.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile pangloss/*.py pangloss/**/*.py`. Review all changed files for: `as any` patterns, empty catches, `print()` in production paths (stderr is OK), commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Compile [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — Full Pipeline** — `unspecified-high`
  Start from clean state (delete `output/`). Run `pangloss generate --verbose`. Verify: 40 concepts processed, `summary.json` has `avg_coverage_pct > 36.25`, `dictionary.json` has collision report, graph files have no `*` prefix. Run `pangloss generate --concept water --verbose` to verify single-concept mode. Run `pangloss generate --format yaml` to verify YAML output. Run pipeline twice to verify caching speedup.
  Output: `Concepts [N/N] | Coverage [X%] | Collisions [FOUND/NONE] | Cache [HIT/MISS] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (`git log/diff`). Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

Each wave gets its own commit(s):
- **Wave 1**: `fix(cli): handle concept name * prefix and YAML filename` + `fix(dictionary): correct coverage statistics`
- **Wave 2**: `feat(coverage): overhaul scoring algorithm for improved coverage`
- **Wave 3**: `feat(algo): add collision detection between concepts` + `feat(phonemes): add fuzzy matching via articulatory features` + `feat(matrix): add caching with hash-based invalidation`
- **Wave 4**: `feat(cli): add tuning knobs and verify full pipeline`

---

## Success Criteria

### Verification Commands
```bash
# After bugs fixed
pangloss generate --concept water --verbose  # Expected: exit 0, concept found
pangloss generate --format yaml && ls output/dictionary.yaml  # Expected: file exists

# After coverage overhaul
pangloss generate --verbose  # Expected: avg_coverage > 36.25%
python -c "import json; d=json.load(open('output/summary.json')); print(d['avg_coverage_pct']); assert d['avg_coverage_pct'] > 36.25"

# After collision detection
python -c "import json; d=json.load(open('output/dictionary.json')); print('collisions' in d)"  # Expected: True

# After caching
time pangloss generate --verbose  # First run: creates cache
time pangloss generate --verbose  # Second run: faster (cache hit)

# Full verification
pangloss generate --verbose --convergence-k 30  # Expected: uses custom k value
```

### Final Checklist
- [ ] All 3 bugs fixed and verified
- [ ] Coverage > 36.25% baseline (target: significant improvement)
- [ ] Collision report in dictionary output
- [ ] Fuzzy matching integrated into convergence + generator
- [ ] Matrix caching working with automatic invalidation
- [ ] CLI tuning knobs functional
- [ ] All 40 concepts processed without errors
- [ ] No `*` in graph filenames
- [ ] No new external dependencies
- [ ] No changes to `graph/trie.py`
