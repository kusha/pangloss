# Pangloss MVP: Data-Driven Synthetic Language Generator

## TL;DR

> **Quick Summary**: Build a Python pipeline that ingests ASJP cross-linguistic phonetic data (568K words, 6,135 languages, 40 core concepts), constructs prefix/suffix bowtie graphs to find phonetic convergence points, and generates synthetic vocabulary words optimized for maximum cross-language recognition — output as a JSON/YAML dictionary with coverage statistics.
> 
> **Deliverables**:
> - ASJP data ingestion module (CLDF CSV parser + CLDR speaker counts)
> - Phoneme segmentation and normalization pipeline
> - Bowtie graph builder (prefix trie + suffix trie + convergence detection)
> - Synthetic word generator (greedy outward expansion from convergence points)
> - Synonym selector (weighted set cover targeting 90% speaker coverage)
> - Dictionary output (JSON/YAML with words, IPA, coverage stats, reasoning)
> - Graph export (JSON for future D3.js visualization)
> - CLI entry point to run the full pipeline
> 
> **Estimated Effort**: Medium-Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Data ingestion → Graph builder → Word generator → Dictionary output

---

## Context

### Original Request
Build "Pangloss" — a data-driven synthetic language generator. The system discovers the most universally recognizable phonetic forms for each concept by analyzing real pronunciations across thousands of languages. For any concept (e.g., "water"), it generates 1-N synthetic synonyms that together cover ≥90% of world speakers, where each synonym targets a different language family cluster.

### Interview Summary
**Key Discussions**:
- End goal is an interactive web dictionary, but MVP is a Python CLI outputting a dictionary file
- Pivoted from Wiktionary scraping to ASJP database as primary data source (pre-segmented IPA, 6,135 languages, CC-BY-4.0)
- Algorithm is novel: "consensus core + optional extensions" — find convergence points where languages cluster phonetically, then expand outward guided by population coverage
- Coverage threshold: 90% absolute speaker coverage (configurable), determines synonym count per concept
- Exact phoneme matching first, fuzzy/distance later
- No automated tests for MVP — manual inspection + agent QA
- Graph persisted as JSON for future D3.js visualization

**Research Findings**:
- ASJP provides 568,820 lexemes across 6,135 languages for 40 Swadesh core concepts with pre-segmented IPA phonemes
- `segments` library (CLLD) handles IPA segmentation reliably; `panphon` for future phonetic distance
- ~40-45 languages cover 99% of world population; top 10 cover 68%
- CLDR provides free speaker count data
- Blasi et al. (2016, PNAS) validated cross-linguistic phonetic patterns exist
- ASJP is complementary (analytical) — Pangloss is generative (creates new words)

### Metis Review
**Identified Gaps** (addressed):
- Concept scope: Confirmed 40 starred core concepts in ASJP's parameters.csv
- Speaker counts: Use CLDR + ASJP raw metadata; CLDF export lacks speaker data
- Bowtie split point: User clarified — deepest shared convergence point across languages, not fixed split
- Fat branch threshold: 90% coverage target + configurable min_languages parameter
- Word generation: Greedy outward expansion from convergence points, not simple prefix × suffix concatenation

---

## Work Objectives

### Core Objective
Process 40 Swadesh core concepts through ASJP's cross-linguistic phonetic data, build bowtie graphs that reveal phonetic convergence patterns, and generate synthetic words that maximize speaker recognition — outputting a complete dictionary file.

### Concrete Deliverables
- `pangloss/` Python package with CLI entry point
- `data/` directory with downloaded ASJP data and CLDR speaker counts
- `output/dictionary.json` — generated synthetic vocabulary
- `output/graphs/` — per-concept bowtie graph JSON files
- `output/summary.json` — coverage statistics and metadata

### Definition of Done
- [ ] `python -m pangloss generate` produces a dictionary covering all 40 ASJP core concepts
- [ ] Each concept has 1-N synonyms achieving ≥90% configurable speaker coverage
- [ ] Each synonym includes: synthetic word form, IPA, covered languages, speaker count, source pattern explanation
- [ ] Bowtie graph JSON exported per concept
- [ ] Summary shows total coverage stats across all concepts

### Must Have
- Parse ASJP CLDF data (forms.csv, parameters.csv, languages.csv)
- Speaker count enrichment (from CLDR or ASJP raw metadata)
- Phoneme-level trie construction (prefix + suffix)
- Convergence point detection (where language families cluster)
- Greedy outward expansion to generate word forms
- Weighted set cover for synonym selection (maximize speaker coverage)
- JSON dictionary output with full reasoning per word
- CLI interface with configurable coverage threshold
- Graph JSON export per concept

### Must NOT Have (Guardrails)
- NO web UI, HTTP server, or frontend code in MVP
- NO live API calls (Google Translate, Wiktionary API, etc.) — offline data only
- NO fuzzy/distance-based phoneme matching — exact only for MVP
- NO phonotactic validation (pronounceability rules) — future enhancement
- NO collision detection between concepts — future enhancement
- NO automated test suite — manual inspection only
- NO database (SQLite, etc.) — file-based I/O only for MVP
- NO over-engineered abstractions — research code, not production framework
- NO hardcoded language lists — derive from data

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (new project)
- **Automated tests**: None (user's explicit choice — research project)
- **Framework**: N/A

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI/Pipeline**: Use Bash — run commands, check exit codes, validate JSON output
- **Data Processing**: Use Bash (Python REPL) — import modules, call functions, inspect results
- **Algorithm Verification**: Use Bash — run pipeline on known concept ("water"), verify output contains expected patterns (e.g., /ak/ cluster for Romance, /vod/ for Slavic)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — all independent, start immediately):
├── Task 1: Project scaffolding + Python package structure [quick]
├── Task 2: Download & parse ASJP CLDF data [unspecified-high]
├── Task 3: Speaker count data acquisition (CLDR) [quick]
└── Task 4: Phoneme normalization utilities [unspecified-high]

Wave 2 (Core data layer — depends on Wave 1):
├── Task 5: Language-concept matrix builder (depends: 2, 3, 4) [deep]
├── Task 6: Prefix trie builder (depends: 4) [deep]
└── Task 7: Suffix trie builder (depends: 4) [deep]

Wave 3 (Algorithm core — depends on Wave 2):
├── Task 8: Convergence point detector (depends: 6, 7) [ultrabrain]
├── Task 9: Greedy outward expansion — word generator (depends: 8, 5) [ultrabrain]
└── Task 10: Synonym selector — weighted set cover (depends: 9, 5) [deep]

Wave 4 (Output + integration — depends on Wave 3):
├── Task 11: Dictionary output formatter (depends: 10) [unspecified-high]
├── Task 12: Graph JSON exporter (depends: 6, 7, 8) [quick]
└── Task 13: CLI entry point + full pipeline integration (depends: 11, 12) [unspecified-high]

Wave FINAL (Verification — after ALL tasks):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Full pipeline QA — run on all 40 concepts [deep]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 2 → Task 5 → Task 8 → Task 9 → Task 10 → Task 11 → Task 13 → F1-F4
Parallel Speedup: ~55% faster than sequential
Max Concurrent: 4 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2-13 (project structure) | 1 |
| 2 | 1 | 5 | 1 |
| 3 | 1 | 5 | 1 |
| 4 | 1 | 5, 6, 7 | 1 |
| 5 | 2, 3, 4 | 9, 10 | 2 |
| 6 | 4 | 8 | 2 |
| 7 | 4 | 8 | 2 |
| 8 | 6, 7 | 9, 12 | 3 |
| 9 | 8, 5 | 10 | 3 |
| 10 | 9, 5 | 11 | 3 |
| 11 | 10 | 13 | 4 |
| 12 | 6, 7, 8 | 13 | 4 |
| 13 | 11, 12 | F1-F4 | 4 |
| F1-F4 | 13 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **4 tasks** — T1 → `quick`, T2 → `unspecified-high`, T3 → `quick`, T4 → `unspecified-high`
- **Wave 2**: **3 tasks** — T5 → `deep`, T6 → `deep`, T7 → `deep`
- **Wave 3**: **3 tasks** — T8 → `ultrabrain`, T9 → `ultrabrain`, T10 → `deep`
- **Wave 4**: **3 tasks** — T11 → `unspecified-high`, T12 → `quick`, T13 → `unspecified-high`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `deep`, F4 → `deep`

---

## TODOs

- [x] 1. Project Scaffolding + Python Package Structure

  **What to do**:
  - Create Python package: `pangloss/` with `__init__.py`, `__main__.py`, `cli.py`
  - Create submodules: `pangloss/data/`, `pangloss/graph/`, `pangloss/algo/`, `pangloss/output/`
  - Each submodule gets `__init__.py`
  - Create `pyproject.toml` with project metadata, Python ≥3.11 requirement
  - Add dependencies: `networkx`, `click` (CLI), `pyyaml`
  - Create `data/` directory (for downloaded datasets)
  - Create `output/` directory (for generated results)
  - Create `.gitignore` for Python, data files, output artifacts
  - Add minimal README.md with project description and usage

  **Must NOT do**:
  - No web framework dependencies (Flask, FastAPI, etc.)
  - No test framework dependencies (pytest, unittest config)
  - No database dependencies (SQLAlchemy, sqlite3 wrappers)
  - No over-engineered plugin systems or dependency injection

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file creation and boilerplate — no complex logic
  - **Skills**: []
    - No specialized skills needed for scaffolding

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2-13 (all tasks need the package structure)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:326-341` — Tech stack section with recommended dependencies and MVP prototype spec

  **External References**:
  - Python packaging guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
  - Click CLI framework: https://click.palletsprojects.com/

  **WHY Each Reference Matters**:
  - The vision doc specifies Python 3.11+ with networkx and graphviz — follow this stack
  - Click is the standard Python CLI framework, keeps the interface clean

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Package structure is importable
    Tool: Bash
    Preconditions: Project scaffolded, venv created
    Steps:
      1. Run: cd /Users/kusha/Sources/pangloss && python -c "import pangloss; print('OK')"
      2. Assert exit code 0 and output contains "OK"
      3. Run: python -c "from pangloss.data import __init__; from pangloss.graph import __init__; from pangloss.algo import __init__; from pangloss.output import __init__"
      4. Assert exit code 0
    Expected Result: All submodules importable without error
    Failure Indicators: ImportError, ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-1-package-import.txt

  Scenario: pyproject.toml is valid
    Tool: Bash
    Preconditions: pyproject.toml exists
    Steps:
      1. Run: python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('valid')"
      2. Assert output contains "valid"
      3. Run: pip install -e . (in a venv)
      4. Assert exit code 0
    Expected Result: Package installs without errors
    Failure Indicators: Invalid TOML, missing required fields
    Evidence: .sisyphus/evidence/task-1-pyproject-valid.txt
  ```

  **Commit**: YES (group with Wave 1)
  - Message: `feat(scaffold): initialize pangloss package structure`
  - Files: `pangloss/**`, `pyproject.toml`, `.gitignore`, `README.md`

- [x] 2. Download & Parse ASJP CLDF Data

  **What to do**:
  - Download ASJP v21 CLDF dataset from Zenodo (https://doi.org/10.5281/zenodo.7836668 or clone https://github.com/lexibank/asjp)
  - Create `pangloss/data/asjp.py` module
  - Parse `cldf/forms.csv`: extract `Language_ID`, `Parameter_ID`, `Value`, `Segments` columns
  - Parse `cldf/parameters.csv`: identify the 40 core concepts (names prefixed with `*`)
  - Parse `cldf/languages.csv`: extract language metadata (name, family, ISO code, geographic coordinates)
  - Build data structures:
    - `ConceptData`: concept_id, name, forms (list of per-language phoneme sequences)
    - `LanguageData`: language_id, name, family, iso_code, coordinates
    - `FormData`: language_id, concept_id, raw_value, ipa_segments (list of phoneme strings)
  - Handle edge cases: missing Segments, multiple forms per language-concept pair, empty entries
  - Filter to only the 40 starred core concepts
  - Provide a function `load_asjp(data_dir: str) -> dict[str, ConceptData]` that returns all parsed data
  - Store the downloaded ASJP data in `data/asjp/` (add to .gitignore)

  **Must NOT do**:
  - No SQLite or database storage — return Python data structures
  - No downloading at runtime — data must be pre-downloaded
  - No custom CSV parsing — use stdlib `csv` module
  - No pandas dependency (keep deps minimal)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Data parsing with edge cases, needs careful handling of CLDF format
  - **Skills**: []
    - No specialized skills — standard Python file I/O

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 5 (language-concept matrix needs parsed data)
  - **Blocked By**: Task 1 (needs package structure)

  **References**:

  **Pattern References**:
  - ASJP forms.csv structure: columns are `ID,Language_ID,Parameter_ID,Value,Form,Segments`
  - ASJP parameters.csv: core concepts have `*` prefix in Name column (e.g., `*water`, `*fire`)
  - Example row: `A51_BAFIA_MAJA-11-1,A51_BAFIA_MAJA,11,fo7,fo7,f o ʔ`

  **External References**:
  - ASJP Lexibank repo: https://github.com/lexibank/asjp (commit `012795349540`)
  - CLDF format spec: https://cldf.clld.org/
  - Zenodo dataset: https://doi.org/10.5281/zenodo.7836668

  **WHY Each Reference Matters**:
  - The `Segments` column contains space-separated IPA phonemes — this is the key column, NOT `Value` (which is ASJPcode)
  - Core concepts are identified by `*` prefix in parameters.csv Name column
  - The CLDF format is standardized CSV with predictable column structure

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Parse all 40 core concepts from ASJP
    Tool: Bash
    Preconditions: ASJP data downloaded to data/asjp/
    Steps:
      1. Run: python -c "from pangloss.data.asjp import load_asjp; data = load_asjp('data/asjp'); print(f'Concepts: {len(data)}'); print(list(data.keys())[:5])"
      2. Assert output shows exactly 40 concepts
      3. Assert concept names include "water", "fire", "sun" (Swadesh basics)
    Expected Result: 40 concepts loaded with names matching ASJP core set
    Failure Indicators: Fewer than 40 concepts, missing expected concepts, KeyError
    Evidence: .sisyphus/evidence/task-2-parse-concepts.txt

  Scenario: Phoneme segments are properly extracted
    Tool: Bash
    Preconditions: ASJP data loaded
    Steps:
      1. Run: python -c "from pangloss.data.asjp import load_asjp; data = load_asjp('data/asjp'); water = data['water']; print(f'Languages with water: {len(water.forms)}'); print(water.forms[0])"
      2. Assert "water" has >100 language forms
      3. Assert each form has a non-empty ipa_segments list
      4. Assert segments are individual phonemes (not full words)
    Expected Result: "water" has hundreds of forms, each with proper phoneme segments
    Failure Indicators: Zero forms, empty segments, unsplit IPA strings
    Evidence: .sisyphus/evidence/task-2-phoneme-segments.txt

  Scenario: Missing/malformed data handled gracefully
    Tool: Bash
    Preconditions: ASJP data loaded
    Steps:
      1. Run: python -c "from pangloss.data.asjp import load_asjp; data = load_asjp('data/asjp'); for concept in data.values(): empty = [f for f in concept.forms if not f.ipa_segments]; print(f'{concept.name}: {len(empty)} empty')"
      2. Assert no exceptions thrown
      3. Assert forms with empty segments are filtered out or flagged
    Expected Result: Graceful handling — no crashes, empty forms filtered
    Failure Indicators: Exception, crash, or silent data corruption
    Evidence: .sisyphus/evidence/task-2-missing-data.txt
  ```

  **Commit**: YES (group with Wave 1)
  - Message: `feat(data): add ASJP CLDF parser for 40 core concepts`
  - Files: `pangloss/data/asjp.py`, `data/asjp/` (gitignored)

- [x] 3. Speaker Count Data Acquisition (CLDR)

  **What to do**:
  - Download CLDR supplemental data (https://github.com/unicode-org/cldr — `common/supplemental/supplementalData.xml` or JSON equivalent from `cldr-core` npm package)
  - Create `pangloss/data/speakers.py` module
  - Parse CLDR `territoryInfo` to extract language populations per territory
  - Aggregate to get total speaker count per language (native + L2)
  - Map CLDR language codes to ASJP language IDs (may need ISO 639-3 as bridge)
  - Provide function `load_speaker_counts() -> dict[str, int]` mapping language_id to total speakers
  - Fallback: for languages not in CLDR, attempt to parse ASJP's `raw/lists.txt` metadata which contains population data
  - Store processed speaker count data as `data/speakers.json` for caching

  **Must NOT do**:
  - No Ethnologue (paid) — CLDR only
  - No live API calls to fetch data
  - No complex NLP for language code matching — simple lookup table

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Data download + XML/JSON parsing, straightforward mapping
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 5 (language-concept matrix needs speaker counts)
  - **Blocked By**: Task 1 (needs package structure)

  **References**:

  **External References**:
  - CLDR GitHub: https://github.com/unicode-org/cldr
  - CLDR supplemental data: `common/supplemental/supplementalData.xml` — contains `<territoryInfo>` with language populations
  - NPM cldr-core package: https://www.npmjs.com/package/cldr-core (JSON format alternative)

  **WHY Each Reference Matters**:
  - CLDR is the only free, maintained source of global speaker count data
  - Territory-level data needs aggregation to get total per language
  - Language code mapping (CLDR uses BCP 47, ASJP uses ISO 639-3) is the main complexity

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Speaker counts loaded for major languages
    Tool: Bash
    Preconditions: CLDR data downloaded
    Steps:
      1. Run: python -c "from pangloss.data.speakers import load_speaker_counts; counts = load_speaker_counts(); print(f'Languages: {len(counts)}'); print({k: v for k, v in sorted(counts.items(), key=lambda x: -x[1])[:10]})"
      2. Assert ≥100 languages have speaker counts
      3. Assert English has >1 billion speakers (native + L2)
      4. Assert Mandarin has >1 billion speakers
    Expected Result: Major languages have plausible speaker counts
    Failure Indicators: Missing major languages, wildly wrong numbers, zero counts
    Evidence: .sisyphus/evidence/task-3-speaker-counts.txt

  Scenario: Speaker counts map to ASJP languages
    Tool: Bash
    Preconditions: Both ASJP and speaker data loaded
    Steps:
      1. Run: python -c "from pangloss.data.asjp import load_asjp; from pangloss.data.speakers import load_speaker_counts; asjp = load_asjp('data/asjp'); counts = load_speaker_counts(); langs = set(); [langs.update(f.language_id for f in c.forms) for c in asjp.values()]; matched = sum(1 for l in langs if l in counts); print(f'ASJP langs: {len(langs)}, Matched: {matched}, Coverage: {matched/len(langs)*100:.1f}%')"
      2. Assert >50% of ASJP languages have speaker counts
    Expected Result: Majority of ASJP languages enriched with speaker data
    Failure Indicators: <20% match rate, mapping failures
    Evidence: .sisyphus/evidence/task-3-asjp-mapping.txt
  ```

  **Commit**: YES (group with Wave 1)
  - Message: `feat(data): add CLDR speaker count data with ASJP mapping`
  - Files: `pangloss/data/speakers.py`, `data/speakers.json`

- [x] 4. Phoneme Normalization Utilities

  **What to do**:
  - Create `pangloss/data/phonemes.py` module
  - Implement phoneme normalization pipeline:
    - Strip tone diacritics (for matching; preserve in output metadata)
    - Strip stress marks (`ˈ`, `ˌ`)
    - Normalize length markers (decide: keep /aː/ as single phoneme or normalize to /a/)
    - Handle combining characters (Unicode NFC normalization)
    - Map common IPA variants to canonical forms (e.g., `g` vs `ɡ`)
  - Implement `normalize_phoneme(phoneme: str) -> str`
  - Implement `normalize_segments(segments: list[str]) -> list[str]` — normalizes each phoneme and filters empty results
  - Implement `segments_to_ipa_string(segments: list[str]) -> str` — join segments back to readable IPA
  - Use the `segments` library (CLLD) if helpful, or implement minimal normalization
  - Document which normalizations are applied and why

  **Must NOT do**:
  - No fuzzy matching or phonetic distance computation (that's future work)
  - No phonotactic validation
  - No language-specific normalization rules — keep it universal

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: IPA/Unicode edge cases require careful handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Tasks 5, 6, 7 (all phoneme processing depends on normalization)
  - **Blocked By**: Task 1 (needs package structure)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:168-192` — IPA conversion caveats: tonal languages, phoneme segmentation details

  **External References**:
  - `segments` library (CLLD): https://github.com/cldf/segments — CLTS-based phoneme tokenization
  - `panphon` FeatureTable: can segment IPA strings into phonemes
  - Unicode NFC normalization: https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize
  - IPA chart reference: https://www.internationalphoneticassociation.org/content/ipa-chart

  **WHY Each Reference Matters**:
  - Vision doc explicitly calls out tone stripping and phoneme segmentation as key challenges
  - ASJP's Segments column is already segmented, but normalization ensures consistency across the dataset
  - Unicode normalization prevents "invisible" mismatches between identical-looking phonemes

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Tone and stress marks stripped correctly
    Tool: Bash
    Preconditions: phonemes module exists
    Steps:
      1. Run: python -c "from pangloss.data.phonemes import normalize_phoneme; print(normalize_phoneme('á')); print(normalize_phoneme('ˈa')); print(normalize_phoneme('aː'))"
      2. Assert tone-marked 'á' → 'a'
      3. Assert stress-marked 'ˈa' → 'a'
      4. Assert length handling is consistent (document which choice was made)
    Expected Result: Diacritics stripped, canonical forms returned
    Failure Indicators: Unchanged diacritics, crash on unusual Unicode
    Evidence: .sisyphus/evidence/task-4-normalization.txt

  Scenario: Full segment normalization pipeline
    Tool: Bash
    Preconditions: phonemes module exists
    Steps:
      1. Run: python -c "from pangloss.data.phonemes import normalize_segments; segs = ['ˈw', 'ɑː', 't', 'ə', 'ɹ']; print(normalize_segments(segs))"
      2. Assert output is a clean list of normalized phonemes
      3. Assert no empty strings in output
    Expected Result: Clean normalized phoneme list
    Failure Indicators: Empty segments, double-normalization artifacts
    Evidence: .sisyphus/evidence/task-4-segment-pipeline.txt
  ```

  **Commit**: YES (group with Wave 1)
  - Message: `feat(data): add IPA phoneme normalization utilities`
  - Files: `pangloss/data/phonemes.py`

- [x] 5. Language-Concept Matrix Builder

  **What to do**:
  - Create `pangloss/data/matrix.py` module
  - Build the central data structure that combines ASJP forms with speaker counts:
    - `ConceptEntry`: for each concept, a list of `(language_id, normalized_phonemes, speaker_count, language_family)` tuples
    - Enrich each form with its language's speaker count from CLDR data
    - For languages without speaker counts, assign a configurable default (e.g., 100,000) or exclude them
  - Implement `build_matrix(asjp_data, speaker_counts) -> dict[str, ConceptEntry]`
  - For each concept, compute summary stats: total languages, total speaker coverage, language families represented
  - Log warnings for languages that couldn't be matched to speaker counts
  - This is the "input layer" that feeds into the graph builder — all downstream tasks consume this structure

  **Must NOT do**:
  - No graph building here — just the flat data structure
  - No filtering by language count or speaker threshold (let downstream tasks handle that)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Data integration across two sources with ID mapping challenges
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Tasks 6, 7 — but those don't depend on this)
  - **Blocks**: Tasks 9, 10 (word generator and synonym selector need speaker-weighted data)
  - **Blocked By**: Tasks 2, 3, 4 (needs ASJP data, speaker counts, and normalized phonemes)

  **References**:

  **Pattern References**:
  - `pangloss/data/asjp.py` (Task 2 output) — ConceptData and FormData structures
  - `pangloss/data/speakers.py` (Task 3 output) — speaker count lookup
  - `pangloss/data/phonemes.py` (Task 4 output) — normalize_segments function

  **WHY Each Reference Matters**:
  - This module is the bridge between raw data (Tasks 2-4) and algorithm (Tasks 6-10)
  - The matrix structure must include speaker counts because the algorithm weights by population
  - Language family metadata enables the visualization to show cluster structure

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Matrix built with speaker-weighted data
    Tool: Bash
    Preconditions: ASJP data and speaker counts loaded
    Steps:
      1. Run: python -c "from pangloss.data.asjp import load_asjp; from pangloss.data.speakers import load_speaker_counts; from pangloss.data.matrix import build_matrix; data = load_asjp('data/asjp'); counts = load_speaker_counts(); matrix = build_matrix(data, counts); water = matrix['water']; print(f'Forms: {len(water.entries)}'); print(f'Total speakers: {sum(e.speaker_count for e in water.entries):,}'); print(water.entries[0])"
      2. Assert water has >100 entries
      3. Assert total speakers > 1 billion (water is universal)
      4. Assert each entry has language_id, phonemes, speaker_count, family
    Expected Result: Rich matrix with speaker-weighted phoneme data
    Failure Indicators: Zero speaker counts, missing fields, fewer entries than ASJP forms
    Evidence: .sisyphus/evidence/task-5-matrix-build.txt
  ```

  **Commit**: YES (group with Wave 2)
  - Message: `feat(data): build speaker-weighted language-concept matrix`
  - Files: `pangloss/data/matrix.py`

- [x] 6. Prefix Trie Builder

  **What to do**:
  - Create `pangloss/graph/trie.py` module
  - Implement a phoneme-level prefix trie using NetworkX DiGraph:
    - Root node at ε (empty string)
    - Each edge represents adding one phoneme to the sequence
    - Each node stores: `phoneme_sequence` (accumulated), `depth`, `languages` (set of language_ids), `speaker_count` (sum of speakers of languages passing through)
    - Each edge stores: `phoneme`, `languages`, `type="prefix"`
  - Implement `build_prefix_trie(entries: list[MatrixEntry]) -> nx.DiGraph`
    - For each language's phoneme sequence, insert into trie left-to-right
    - At each node, accumulate the language_id and its speaker count
  - Implement `get_node_score(node) -> float` — `depth * speaker_count` (as per vision doc)
  - The trie should be serializable to JSON for the graph exporter
  - Include metadata on the graph: concept name, total languages, build parameters

  **Must NOT do**:
  - No suffix trie here (that's Task 7)
  - No bridge edges or convergence detection (Task 8)
  - No custom trie implementation — use NetworkX DiGraph as the backing store

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Graph algorithm implementation with careful node/edge attribute management
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (parallel with Task 7)
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: Task 8 (convergence detector needs both tries)
  - **Blocked By**: Task 4 (needs normalized phonemes), Task 1 (needs package structure)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:43-103` — Complete bowtie graph structure spec: node types, edge types, properties
  - `.sisyphus/reference/phonetic-lingua.md:174-192` — Python pseudocode for `build_prefix_trie`

  **External References**:
  - NetworkX DiGraph: https://networkx.org/documentation/stable/reference/classes/digraph.html
  - NetworkX `prefix_tree()`: built-in function (may be useful as reference, though custom implementation needed)
  - NetworkX JSON export: `networkx.readwrite.json_graph.node_link_data()`

  **WHY Each Reference Matters**:
  - The vision doc has detailed node/edge property specs — follow them exactly
  - The pseudocode shows the insertion algorithm — adapt for real implementation
  - NetworkX's JSON export will feed into the graph exporter (Task 12)

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Prefix trie built for "water"
    Tool: Bash
    Preconditions: Matrix data available for "water"
    Steps:
      1. Run: python -c "
         from pangloss.data.asjp import load_asjp
         from pangloss.data.speakers import load_speaker_counts
         from pangloss.data.matrix import build_matrix
         from pangloss.graph.trie import build_prefix_trie
         data = load_asjp('data/asjp')
         counts = load_speaker_counts()
         matrix = build_matrix(data, counts)
         trie = build_prefix_trie(matrix['water'].entries)
         print(f'Nodes: {trie.number_of_nodes()}, Edges: {trie.number_of_edges()}')
         root_children = list(trie.successors('ε'))
         print(f'Root branches: {len(root_children)}')
         for child in sorted(root_children)[:5]:
           n = trie.nodes[child]
           print(f'  {child}: {len(n[\"languages\"])} langs, {n[\"speaker_count\"]:,} speakers')
         "
      2. Assert trie has >50 nodes (many phoneme paths)
      3. Assert root has multiple children (different initial phonemes)
      4. Assert each node has languages set and speaker_count
    Expected Result: Multi-branching trie with speaker-weighted nodes showing language family clusters
    Failure Indicators: Single-path trie, zero speaker counts, missing language sets
    Evidence: .sisyphus/evidence/task-6-prefix-trie.txt

  Scenario: Trie nodes show language family clustering
    Tool: Bash
    Preconditions: Prefix trie built for "water"
    Steps:
      1. Navigate trie from root through /a/ → /k/ path
      2. Assert this path contains Romance languages (es, pt, it, fr for "aqua/agua")
      3. Navigate through /v/ → /o/ path
      4. Assert this path contains Slavic languages (ru, pl, cs for "voda")
    Expected Result: Language families naturally cluster on shared prefix paths
    Failure Indicators: Random language distribution, no clustering visible
    Evidence: .sisyphus/evidence/task-6-clustering.txt
  ```

  **Commit**: YES (group with Wave 2)
  - Message: `feat(graph): implement phoneme-level prefix trie builder`
  - Files: `pangloss/graph/trie.py`

- [x] 7. Suffix Trie Builder

  **What to do**:
  - Extend `pangloss/graph/trie.py` (or create `pangloss/graph/suffix_trie.py`)
  - Implement suffix trie: identical to prefix trie but phoneme sequences are REVERSED before insertion
  - Implement `build_suffix_trie(entries: list[MatrixEntry]) -> nx.DiGraph`
    - For each language's phoneme sequence, reverse it, then insert into trie
    - Same node/edge properties as prefix trie, but `type="suffix"`
  - The suffix trie captures shared word endings — morphological patterns like vowel endings, common suffixes
  - Reuse as much code as possible from Task 6 (the core trie insertion is identical, just reversed input)

  **Must NOT do**:
  - No bridge edges (Task 8)
  - No duplication of trie logic — factor out shared `_insert_into_trie()` function

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Must integrate with prefix trie code, ensure consistent node structure
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (parallel with Task 6)
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 8 (convergence detector needs both tries)
  - **Blocked By**: Task 4 (needs normalized phonemes), Task 1 (needs package structure)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:43-103` — Bowtie graph structure: suffix trie grows right←left
  - `.sisyphus/reference/phonetic-lingua.md:186-192` — Python pseudocode for `build_suffix_trie` (reverse phonemes then insert)
  - `pangloss/graph/trie.py` (Task 6 output) — prefix trie implementation to share code with

  **WHY Each Reference Matters**:
  - The vision doc shows suffix trie mirrors prefix trie with reversed input
  - Code reuse between prefix and suffix is critical to avoid bugs from divergent implementations

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Suffix trie built for "water" captures ending patterns
    Tool: Bash
    Preconditions: Matrix data available
    Steps:
      1. Build suffix trie for "water"
      2. Print root children (most common final phonemes)
      3. Assert the trie has branches for common endings like /a/ (many languages end words in vowels)
      4. Assert node properties match prefix trie structure (languages, speaker_count, depth)
    Expected Result: Suffix trie shows clustering by word endings
    Failure Indicators: Identical to prefix trie (not reversed), missing properties
    Evidence: .sisyphus/evidence/task-7-suffix-trie.txt
  ```

  **Commit**: YES (group with Wave 2)
  - Message: `feat(graph): implement suffix trie builder (reversed phoneme insertion)`
  - Files: `pangloss/graph/trie.py` (extended) or `pangloss/graph/suffix_trie.py`

- [x] 8. Convergence Point Detector

  **What to do**:
  - Create `pangloss/algo/convergence.py` module
  - This is the CORE NOVEL ALGORITHM. The goal: find the phoneme position(s) in each concept's word set where the most languages converge — these become the "seeds" from which synthetic words grow outward.
  - Algorithm design (creative implementation needed):
    1. For each language's phoneme sequence for a concept, consider ALL possible split points (e.g., for a 5-phoneme word: positions 1, 2, 3, 4)
    2. At each split point, the LEFT portion goes into the prefix trie, the RIGHT portion (reversed) into the suffix trie
    3. A "convergence point" is a (prefix_node, suffix_node) pair where the intersection of their language sets is maximized, weighted by speaker count
    4. Find the TOP-K convergence points that together cover the most speakers (this feeds into synonym selection)
  - Implement `find_convergence_points(prefix_trie, suffix_trie, entries, k=10) -> list[ConvergencePoint]`
  - Each `ConvergencePoint` contains:
    - `prefix_phonemes`: the shared prefix sequence (e.g., /ak/)
    - `suffix_phonemes`: the shared suffix sequence (e.g., /a/)
    - `languages`: set of languages that share BOTH this prefix and suffix
    - `speaker_count`: total speakers of those languages
    - `depth`: combined prefix + suffix depth (word length indicator)
    - `score`: `depth * speaker_count` (or similar composite)
  - IMPORTANT: The prefix trie and suffix trie are already built (Tasks 6, 7). This task connects them by finding which prefix paths and suffix paths belong to the SAME languages, and where those connections are densest.
  - Consider: bridge edges in the bowtie graph connect each language's deepest prefix node to its deepest suffix node. The convergence points are where many bridge edges cluster.

  **Must NOT do**:
  - No word generation here (Task 9) — only find the convergence points
  - No synonym selection (Task 10) — just return ranked candidates
  - Don't optimize prematurely — correctness first, even if O(n²)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Novel algorithm design with no prior art. Requires creative problem-solving and graph algorithm expertise.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential — 8 must complete before 9)
  - **Blocks**: Tasks 9, 12 (word generator needs convergence points; graph exporter needs bridge edge data)
  - **Blocked By**: Tasks 6, 7 (needs both tries built)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:43-103` — Bowtie graph structure with bridge edges connecting prefix to suffix
  - `.sisyphus/reference/phonetic-lingua.md:196-210` — Fat branch extraction algorithm: `score_node` and `extract_fat_branches` pseudocode
  - `.sisyphus/reference/phonetic-lingua.md:99-103` — Why fat branches = phonetic universals; language families emerge from the graph

  **External References**:
  - Weighted set cover problem: https://en.wikipedia.org/wiki/Set_cover_problem (the convergence selection is a variant)
  - NetworkX subgraph algorithms: useful for finding connected components in the bridge edge layer

  **WHY Each Reference Matters**:
  - The vision doc's scoring formula `depth * speaker_count` is the starting point, but may need refinement
  - The bowtie bridge edge concept is key: each language creates one bridge edge from its deepest prefix to its deepest suffix — convergence points are where bridges cluster
  - This is where the "find the deepest shared midpoint" insight from the user applies

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Convergence points found for "water" show expected clusters
    Tool: Bash
    Preconditions: Prefix and suffix tries built for "water"
    Steps:
      1. Run convergence detection on "water"
      2. Print top 5 convergence points with their languages and speaker counts
      3. Assert at least one convergence point covers Romance languages with prefix /ak/ or similar
      4. Assert at least one covers Slavic languages with prefix /v/ or /vo/
      5. Assert at least one covers Germanic languages with prefix /w/ or /va/
      6. Assert speaker counts are plausible (top point should cover >500M speakers)
    Expected Result: Convergence points correspond to known language family phonetic clusters
    Failure Indicators: Random convergence points, single-language points, zero coverage
    Evidence: .sisyphus/evidence/task-8-convergence-water.txt

  Scenario: Convergence points are distinct (not overlapping)
    Tool: Bash
    Preconditions: Convergence detection complete
    Steps:
      1. Check that top convergence points cover DIFFERENT language sets
      2. Assert language intersection between top-3 points is <20% of each point's languages
    Expected Result: Points target different language families, not the same languages
    Failure Indicators: All points cover the same languages, heavy overlap
    Evidence: .sisyphus/evidence/task-8-convergence-distinct.txt
  ```

  **Commit**: YES (group with Wave 3)
  - Message: `feat(algo): implement convergence point detection in bowtie graph`
  - Files: `pangloss/algo/convergence.py`

- [x] 9. Greedy Outward Expansion — Word Generator

  **What to do**:
  - Create `pangloss/algo/generator.py` module
  - Given a convergence point (prefix seed + suffix seed), generate a synthetic word by expanding outward:
    1. Start with the convergence point's phoneme core (e.g., /ak/ from prefix + /a/ from suffix → /aka/)
    2. Consider extending LEFT: adding a phoneme before the prefix. Score the extension by: does it increase speaker coverage meaningfully? Does it make the word more distinctive?
    3. Consider extending RIGHT: adding a phoneme after the suffix. Same scoring.
    4. Greedily add extensions while they improve the score above a threshold
    5. Stop when extensions no longer add meaningful coverage
  - Implement `generate_word(convergence_point, prefix_trie, suffix_trie, entries) -> SyntheticWord`
  - Each `SyntheticWord` contains:
    - `phonemes`: list of phonemes in the synthetic word
    - `ipa`: IPA string representation
    - `form`: romanized/readable form (best effort — simplified IPA to Latin)
    - `covered_languages`: set of language_ids this word would be recognizable to
    - `speaker_count`: total speakers covered
    - `coverage_pct`: percentage of world speakers covered
    - `reasoning`: human-readable explanation of why this form was chosen
  - The `reasoning` field is important: it should explain "This word starts with /ak/ because 15 Romance + 3 Turkic languages share this prefix for 'water', covering 1.8B speakers. The /a/ suffix was added because..."
  - Handle edge cases: convergence point with very short core (1 phoneme), no beneficial extensions available

  **Must NOT do**:
  - No synonym selection here (Task 10) — generate ONE word per convergence point
  - No collision detection between concepts
  - No phonotactic validation (whether the word is pronounceable)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Novel generative algorithm. Requires creative scoring function design and balancing coverage vs. word length.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 8)
  - **Blocks**: Task 10 (synonym selector needs generated words)
  - **Blocked By**: Tasks 8, 5 (needs convergence points and speaker-weighted matrix)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:259-293` — Recognition score model: prefix weighted 2x over suffix, phoneme overlap
  - `.sisyphus/reference/phonetic-lingua.md:214-248` — Synonym selection pseudocode (the set cover part is Task 10, but the word combination logic informs this task)
  - User's algorithm description: "from midpoint, go left and right, decide if suffix/prefix is necessary by population and by distinction from other existing words"

  **External References**:
  - Greedy algorithms: the expansion is analogous to greedy feature selection in ML

  **WHY Each Reference Matters**:
  - The vision doc's recognition score (prefix 2x, suffix 1x) should inform the extension scoring
  - The user's insight about "distinction from other existing words" means the generator should prefer extensions that disambiguate this concept from others — even though collision detection is out of MVP scope, the reasoning framework should be built to support it
  - The word form generation (IPA → readable) needs simple transliteration, not a full system

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Generate synthetic word for "water" from Romance convergence point
    Tool: Bash
    Preconditions: Convergence points found for "water"
    Steps:
      1. Take the Romance-cluster convergence point (should have /ak/ prefix)
      2. Run word generator
      3. Print resulting word: form, IPA, covered languages, speaker count, reasoning
      4. Assert the generated word contains /ak/ or similar Romance phonemes
      5. Assert it covers >10 languages and >500M speakers
      6. Assert reasoning field is non-empty and mentions language families
    Expected Result: A word like "aka" or "akwa" with Romance + related language coverage
    Failure Indicators: Empty word, zero coverage, no reasoning
    Evidence: .sisyphus/evidence/task-9-word-water-romance.txt

  Scenario: Generated words have reasonable length
    Tool: Bash
    Preconditions: Word generator functional
    Steps:
      1. Generate words for multiple convergence points across different concepts
      2. Assert word lengths are 2-8 phonemes (reasonable for a natural-sounding word)
      3. Assert no single-phoneme words (too ambiguous)
      4. Assert no >10-phoneme words (too complex for recognition)
    Expected Result: Words are natural-length, pronounceable-looking
    Failure Indicators: Single phoneme words, extremely long words, empty phoneme lists
    Evidence: .sisyphus/evidence/task-9-word-lengths.txt
  ```

  **Commit**: YES (group with Wave 3)
  - Message: `feat(algo): implement greedy outward word generation from convergence points`
  - Files: `pangloss/algo/generator.py`

- [x] 10. Synonym Selector — Weighted Set Cover

  **What to do**:
  - Create `pangloss/algo/selector.py` module
  - Given multiple candidate words (from multiple convergence points), select the minimum set of synonyms that achieves the target coverage (default 90%):
    1. Start with all candidate words and their covered language sets
    2. Greedy selection: pick the word covering the most UNCOVERED speakers
    3. Remove covered languages from the uncovered set
    4. Repeat until coverage threshold reached or no more candidates improve coverage
  - Implement `select_synonyms(candidates: list[SyntheticWord], coverage_threshold: float = 0.9) -> list[SyntheticWord]`
  - The output list is ordered by coverage contribution (largest first)
  - Each synonym gets a `coverage_delta` field: how much additional coverage it adds
  - Compute total coverage stats: total speakers covered, total percentage, number of synonyms needed
  - Handle edge case: if maximum achievable coverage is below threshold, return all useful synonyms and note the gap

  **Must NOT do**:
  - No complex optimization (ILP, branch-and-bound) — greedy is fine for MVP
  - No inter-concept synonym coordination

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Classic weighted set cover implementation, but needs careful integration with the word generator output
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 9)
  - **Blocks**: Task 11 (dictionary output needs selected synonyms)
  - **Blocked By**: Tasks 9, 5 (needs generated words and speaker data)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:214-248` — Complete `select_synonyms` pseudocode with greedy weighted set cover
  - User's decision: "90% absolute coverage, but configurable and based on number of synonyms we can decide"

  **External References**:
  - Greedy set cover: https://en.wikipedia.org/wiki/Set_cover_problem#Greedy_algorithm

  **WHY Each Reference Matters**:
  - The vision doc has working pseudocode for this exact algorithm — adapt it
  - The 90% threshold is configurable — make it a parameter with 0.9 default
  - The user wants to see how many synonyms different thresholds produce

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Synonym selection for "water" achieves 90% coverage
    Tool: Bash
    Preconditions: Multiple candidate words generated for "water"
    Steps:
      1. Run synonym selection with 0.9 threshold
      2. Print selected synonyms: form, coverage delta, cumulative coverage
      3. Assert total coverage ≥ 90% (or best achievable with note)
      4. Assert 1-5 synonyms selected (reasonable for a common concept)
      5. Assert synonyms cover DIFFERENT language families (not all Romance)
    Expected Result: 2-3 synonyms covering 90%+ speakers, each targeting different language clusters
    Failure Indicators: Single synonym claimed at 90%, all synonyms from same family, <50% total coverage
    Evidence: .sisyphus/evidence/task-10-synonyms-water.txt

  Scenario: Coverage threshold is configurable
    Tool: Bash
    Preconditions: Synonym selection functional
    Steps:
      1. Run with threshold 0.5 — expect fewer synonyms
      2. Run with threshold 0.99 — expect more synonyms
      3. Assert synonym count increases with higher threshold
    Expected Result: Higher threshold = more synonyms needed
    Failure Indicators: Same synonym count regardless of threshold
    Evidence: .sisyphus/evidence/task-10-threshold-config.txt
  ```

  **Commit**: YES (group with Wave 3)
  - Message: `feat(algo): implement weighted set cover synonym selection`
  - Files: `pangloss/algo/selector.py`

- [x] 11. Dictionary Output Formatter

  **What to do**:
  - Create `pangloss/output/dictionary.py` module
  - Format the full pipeline results into a structured dictionary file:
    - For each of the 40 concepts, output:
      - `concept`: the English concept name
      - `synonyms`: list of selected synthetic words, each with:
        - `form`: readable spelling
        - `ipa`: IPA representation
        - `covers`: list of language codes this synonym covers
        - `speaker_count`: total speakers covered by this synonym
        - `coverage_pct`: percentage of world speakers
        - `source_pattern`: human-readable description (e.g., "Latin 'aqua' family")
        - `reasoning`: full algorithmic reasoning trail
      - `total_coverage`: combined coverage of all synonyms
      - `total_speakers`: combined speaker count
      - `language_families_covered`: list of language families represented
      - `synonym_count`: how many synonyms were needed
  - Implement `format_dictionary(results: dict[str, list[SyntheticWord]]) -> dict`
  - Implement `save_dictionary(dictionary: dict, path: str, format: str = "json")` — supports JSON and YAML
  - Also generate `output/summary.json`: aggregate stats across all 40 concepts (avg coverage, min/max, total unique languages, etc.)

  **Must NOT do**:
  - No HTML/web output
  - No pretty-printing beyond standard JSON indentation
  - No concept-relationship metadata (morphology, compounds)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Data serialization with specific schema requirements
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (parallel with Task 12)
  - **Parallel Group**: Wave 4 (with Tasks 12, 13)
  - **Blocks**: Task 13 (CLI needs dictionary output function)
  - **Blocked By**: Task 10 (needs selected synonyms)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:22-39` — Example output YAML showing the target dictionary format
  - `.sisyphus/reference/phonetic-lingua.md:250-257` — Output spec: synthetic word(s) with IPA, covered languages, speaker count, graph visualization

  **WHY Each Reference Matters**:
  - The vision doc shows the exact output format the user envisioned — match this structure
  - The YAML example (water: aka, voda, watr) is the gold standard for what the output should look like

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Dictionary JSON is valid and complete
    Tool: Bash
    Preconditions: Pipeline has generated results for all 40 concepts
    Steps:
      1. Run: python -c "import json; d = json.load(open('output/dictionary.json')); print(f'Concepts: {len(d[\"concepts\"])}'); c = d['concepts'][0]; print(f'First: {c[\"concept\"]} with {c[\"synonym_count\"]} synonyms, {c[\"total_coverage\"]*100:.1f}% coverage')"
      2. Assert 40 concepts in output
      3. Assert each concept has ≥1 synonym
      4. Assert each synonym has all required fields (form, ipa, covers, speaker_count, reasoning)
      5. Assert JSON is valid (no parsing errors)
    Expected Result: Complete, valid dictionary with all 40 concepts and full metadata
    Failure Indicators: Missing concepts, missing fields, invalid JSON
    Evidence: .sisyphus/evidence/task-11-dictionary-valid.txt

  Scenario: Summary statistics are accurate
    Tool: Bash
    Preconditions: Dictionary and summary generated
    Steps:
      1. Load summary.json
      2. Assert average coverage > 70% (most concepts should achieve good coverage)
      3. Assert total unique languages > 100
      4. Assert min synonym count ≥ 1, max ≤ 10
    Expected Result: Plausible aggregate statistics
    Failure Indicators: 0% coverage, negative counts, impossible values
    Evidence: .sisyphus/evidence/task-11-summary-stats.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Message: `feat(output): add dictionary and summary JSON formatters`
  - Files: `pangloss/output/dictionary.py`

- [x] 12. Graph JSON Exporter

  **What to do**:
  - Create `pangloss/output/graph_export.py` module
  - Export the bowtie graph (prefix trie + suffix trie + convergence/bridge edges) as JSON per concept
  - Use NetworkX's `node_link_data()` for serialization
  - Each exported graph should include:
    - All prefix trie nodes and edges
    - All suffix trie nodes and edges
    - Bridge edges from convergence detection (which prefix nodes connect to which suffix nodes)
    - Node metadata: phoneme sequence, depth, languages, speaker count
    - Edge metadata: type (prefix/suffix/bridge), languages, weight
    - Graph metadata: concept name, total languages, convergence points used
  - Save to `output/graphs/{concept_name}.json`
  - These files will later feed into D3.js visualization (future work)

  **Must NOT do**:
  - No visualization rendering — just JSON export
  - No D3.js code or HTML generation
  - No graph optimization or layout computation

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward NetworkX → JSON serialization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (parallel with Task 11)
  - **Parallel Group**: Wave 4 (with Tasks 11, 13)
  - **Blocks**: Task 13 (CLI calls graph export)
  - **Blocked By**: Tasks 6, 7, 8 (needs tries and convergence data)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:43-103` — Complete bowtie graph structure spec
  - `pangloss/graph/trie.py` (Tasks 6, 7) — trie structures to serialize
  - `pangloss/algo/convergence.py` (Task 8) — convergence points to include as bridge edges

  **External References**:
  - NetworkX JSON export: `networkx.readwrite.json_graph.node_link_data()` — standard serialization
  - D3.js force graph data format: https://d3js.org/d3-force (for future compatibility)

  **WHY Each Reference Matters**:
  - NetworkX's node_link_data produces JSON that's almost directly consumable by D3.js force layouts
  - The bowtie structure needs all three components (prefix, suffix, bridge) in one JSON

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Graph JSON exported for each concept
    Tool: Bash
    Preconditions: Tries and convergence data available
    Steps:
      1. Run graph export for all concepts
      2. Run: ls output/graphs/ | wc -l
      3. Assert 40 JSON files exist
      4. Run: python -c "import json; g = json.load(open('output/graphs/water.json')); print(f'Nodes: {len(g[\"nodes\"])}, Links: {len(g[\"links\"])}')"
      5. Assert water graph has >20 nodes and >20 links
      6. Assert link types include "prefix", "suffix", and "bridge"
    Expected Result: Valid graph JSON files for all 40 concepts
    Failure Indicators: Missing files, empty graphs, missing edge types
    Evidence: .sisyphus/evidence/task-12-graph-export.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Message: `feat(output): add bowtie graph JSON exporter`
  - Files: `pangloss/output/graph_export.py`

- [ ] 13. CLI Entry Point + Full Pipeline Integration

  **What to do**:
  - Implement `pangloss/cli.py` using Click framework
  - Create main command: `python -m pangloss generate`
    - Options:
      - `--data-dir` (default: `data/asjp`) — path to ASJP data
      - `--output-dir` (default: `output/`) — where to write results
      - `--coverage-threshold` (default: `0.9`) — target coverage for synonym selection
      - `--concept` (optional) — process a single concept instead of all 40
      - `--format` (default: `json`) — output format (json/yaml)
      - `--verbose` flag — print progress and per-concept summaries
  - Wire together the full pipeline:
    1. Load ASJP data (`pangloss.data.asjp.load_asjp`)
    2. Load speaker counts (`pangloss.data.speakers.load_speaker_counts`)
    3. Build matrix (`pangloss.data.matrix.build_matrix`)
    4. For each concept:
       a. Normalize phonemes
       b. Build prefix trie
       c. Build suffix trie
       d. Find convergence points
       e. Generate candidate words
       f. Select synonyms
       g. Export graph JSON
    5. Format and save dictionary
    6. Format and save summary
    7. Print final stats to stdout
  - Implement `pangloss/__main__.py` to enable `python -m pangloss`
  - Handle errors gracefully: if one concept fails, log error and continue with remaining concepts
  - Progress output: print concept name and coverage as each completes

  **Must NOT do**:
  - No interactive mode or REPL
  - No web server or API endpoints
  - No watch mode or file monitoring
  - No parallel/async processing (sequential is fine for 40 concepts)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration of all modules, error handling, CLI design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (integration task)
  - **Parallel Group**: Wave 4 (after Tasks 11, 12)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: Tasks 11, 12 (needs all output formatters)

  **References**:

  **Pattern References**:
  - `.sisyphus/reference/phonetic-lingua.md:109-134` — Pipeline diagram showing the flow: Translate → IPA → Graph → Extract → Select → Output
  - All Task outputs (1-12) — this task wires them together

  **External References**:
  - Click CLI framework: https://click.palletsprojects.com/en/stable/
  - Click options and arguments: https://click.palletsprojects.com/en/stable/options/

  **WHY Each Reference Matters**:
  - The vision doc's pipeline diagram is the integration spec — follow the flow exactly
  - Click provides clean CLI with help text, type validation, and default values

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: Full pipeline runs end-to-end on all 40 concepts
    Tool: Bash
    Preconditions: All modules implemented, ASJP data downloaded
    Steps:
      1. Run: python -m pangloss generate --verbose --coverage-threshold 0.9
      2. Assert exit code 0
      3. Assert stdout shows progress for each concept
      4. Assert output/dictionary.json exists and has 40 concepts
      5. Assert output/summary.json exists
      6. Assert output/graphs/ has 40 .json files
    Expected Result: Complete pipeline execution with all outputs generated
    Failure Indicators: Non-zero exit, missing output files, crashes mid-run
    Evidence: .sisyphus/evidence/task-13-full-pipeline.txt

  Scenario: Single concept mode works
    Tool: Bash
    Preconditions: Pipeline functional
    Steps:
      1. Run: python -m pangloss generate --concept water --verbose
      2. Assert output shows only "water" processing
      3. Assert dictionary.json contains only one concept
    Expected Result: Single concept processed successfully
    Failure Indicators: All concepts processed, crash on filtering
    Evidence: .sisyphus/evidence/task-13-single-concept.txt

  Scenario: Error in one concept doesn't crash the pipeline
    Tool: Bash
    Preconditions: Pipeline functional
    Steps:
      1. Verify that if one concept has unusual data (very few languages), the pipeline logs a warning and continues
      2. Assert final output includes all concepts that succeeded
    Expected Result: Graceful degradation — skip failed concepts, process rest
    Failure Indicators: Pipeline crashes on first error, no error logging
    Evidence: .sisyphus/evidence/task-13-error-handling.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Message: `feat(cli): add full pipeline CLI with configurable coverage threshold`
  - Files: `pangloss/cli.py`, `pangloss/__main__.py`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile pangloss/*.py`. Review all files for: bare excepts, hardcoded paths, missing type hints on public APIs, commented-out code, unused imports. Check for AI slop: excessive comments, over-abstraction, generic variable names. Verify package structure is clean.
  Output: `Compile [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Full Pipeline QA** — `deep`
  Run `python -m pangloss generate --coverage-threshold 0.9` and verify:
  - Produces output for all 40 concepts
  - Each concept has ≥1 synonym
  - Total speaker coverage per concept ≥ 90% (or best achievable)
  - Output JSON is valid and contains required fields (form, ipa, covers, speaker_count, reasoning)
  - Graph JSON files produced per concept
  - Summary statistics are accurate
  - Run on a single concept ("water") and verify output contains expected patterns: should see Romance /ak/ cluster, Slavic /vod/ cluster, Germanic /wat/ cluster
  Output: `Concepts [N/N] | Coverage [min/avg/max %] | JSON Valid [Y/N] | Graphs [N/N] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual implementation. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Flag any web UI code, API calls, SQLite usage, test frameworks, or over-engineered abstractions.
  Output: `Tasks [N/N compliant] | Creep [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- After Wave 1: `feat(data): add ASJP ingestion, speaker counts, and phoneme utilities`
- After Wave 2: `feat(graph): implement prefix/suffix trie builders and language-concept matrix`
- After Wave 3: `feat(algo): add convergence detection, word generation, and synonym selection`
- After Wave 4: `feat(cli): add dictionary output, graph export, and CLI entry point`

---

## Success Criteria

### Verification Commands
```bash
python -m pangloss generate --coverage-threshold 0.9  # Expected: dictionary.json with 40 concepts
python -m pangloss generate --concept water             # Expected: synonyms covering ≥90% speakers
cat output/dictionary.json | python -m json.tool         # Expected: valid JSON
ls output/graphs/                                        # Expected: 40 .json files
```

### Final Checklist
- [ ] All 40 ASJP core concepts processed
- [ ] Each concept has synthetic word(s) with ≥90% speaker coverage
- [ ] Dictionary JSON includes: form, IPA, covered languages, speaker count, reasoning
- [ ] Bowtie graph JSON exported per concept
- [ ] CLI runs end-to-end without errors
- [ ] No web UI, API calls, databases, or test frameworks in codebase
- [ ] Code is research-quality Python (readable, not over-engineered)
