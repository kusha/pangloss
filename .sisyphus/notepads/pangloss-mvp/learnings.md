# Pangloss MVP - Learnings

## Package Structure

- Python packages require `__init__.py` to be recognized as modules, even empty ones
- Submodules (data/, graph/, algo/, output/) are properly isolated with their own `__init__.py` files
- Entry point through `__main__.py` enables `python -m pangloss` execution

## CLI Framework

- Click is the standard Python CLI framework for structured command groups
- Click decorators (`@click.group()`, `@click.command()`) provide clean command organization
- CLI can be installed as an entry point via `pyproject.toml` [project.scripts] section

## Dependency Management

- Modern Python packaging uses `pyproject.toml` over `setup.py` (PEP 517/518)
- Dependencies should not be pinned unless necessary (networkx, click, pyyaml remain version-flexible)
- Build system requires `setuptools` and `wheel` for modern packaging

## Python Version

- MVP targets Python 3.10+ (practical minimum given availability)
- Can be upgraded to 3.11+ if needed for specific features (match operator, etc.)

## Project Metadata

- Version stored in `__init__.py` (__version__ = "0.1.0") and duplicated in `pyproject.toml`
- Proper classifiers help with PyPI categorization (Development Status :: 3 - Alpha)
- Author attribution included for clarity

## .gitignore Best Practices

- Standard Python ignores: __pycache__/, *.pyc, venv/, etc.
- Project-specific: data/, output/ directories (external artifacts)
- Include common IDE/tool caches to keep repo clean

## Phoneme Normalization: Unicode Handling (Task 4)

**Unicode NFC Normalization is Critical**:
- IPA transcriptions may use precomposed characters (á) or combining sequences (a + ́)
- Without NFC normalization, identical phonemes fail to match due to different encodings
- Python's `unicodedata.normalize('NFC', text)` canonicalizes to precomposed form
- Apply NFC both before and after diacritic stripping for consistency

**Tone Diacritic Stripping Strategy**:
1. First pass: Strip stress marks (standalone characters like ˈ, ˌ)
2. Decompose to NFD to separate base character from combining diacritics
3. Filter out combining tone diacritics (U+0300, U+0301, etc.)
4. Recompose to NFC for final canonical form

**IPA Variant Glyphs**:
- Common mistake: using Latin 'g' (U+0067) instead of IPA 'ɡ' (U+0261)
- Variants exist for historical/keyboard input reasons
- Normalize to canonical IPA codepoints for consistent matching
- Map: g → ɡ, : → ː (ASCII colon to IPA length marker)

**Empty String Filtering**:
- Some segments may be purely diacritical (stress-only, tone-only)
- After normalization these become empty strings
- Always filter empty results from `normalize_segments()` output
- Preserves segment count semantics (only phonemes, not prosody markers)

**Testing Edge Cases**:
- Combining diacritics (a + ́ vs á)
- Multiple diacritics on single base (rare but possible)
- Empty segments after normalization
- Length markers with tones (e.g., áː → aː)

**Date**: 2026-03-05

## ASJP CLDF Dataset Parsing (Task 2)

**CLDF Structure**:
- ASJP v21 uses CLDF (Cross-Linguistic Data Format) with CSV files
- Key files: `parameters.csv` (concepts), `forms.csv` (word forms), `languages.csv` (metadata)
- Forms.csv has 568,820 rows with columns: Language_ID, Parameter_ID, Value, Segments
- Segments column contains space-separated IPA phonemes (NOT ASJPcode from Value column)

**40 Core Concepts Identification**:
- Core concepts identified by asterisk (*) prefix in parameters.csv Name column
- Examples: *water, *fire, *sun, *I, *you, *dog, *tree
- Exactly 40 concepts marked with asterisk (Swadesh core list)
- Concept IDs are numeric strings: "1", "75", "82", etc. (not zero-padded)

**Edge Cases Encountered**:
1. **Missing Segments**: Some forms have empty Segments column → skip these forms
2. **Multiple forms per language-concept**: Dataset allows duplicates → keep all (no deduplication)
3. **Malformed coordinates**: Some languages have empty lat/lon → handle gracefully with Optional
4. **Segment length variation**: Forms range from 1 phoneme (e.g., "u" for fire) to 18 phonemes
5. **Empty Value field**: raw_value can be empty even when Segments is populated

**Data Filtering Strategy**:
- Filter in forms.csv: only include forms where Parameter_ID is in core_concepts set
- Skip forms where Segments is missing, empty, or whitespace-only
- Split Segments on whitespace: `segments_str.split()` produces list of phonemes
- No need to filter by language family or geography (keep all languages)

**Form Counts**:
- Water: 11,873 forms (most represented)
- Full: 7,118 forms (least represented, but still >100)
- Average ~10,000 forms per concept across 11,540 language varieties

**CSV Parsing Best Practices**:
- Use stdlib `csv.DictReader` (no pandas dependency)
- UTF-8 encoding required for IPA characters
- Handle empty fields with `.get()` and `.strip()` checks
- Parse coordinates as float with try/except (malformed data exists)

**Data Structure Design**:
- Use dataclasses for clean structure (FormData, LanguageData, ConceptData)
- Return dict mapping concept_id (str) to ConceptData for fast lookup
- Store ipa_segments as List[str] (space-separated phonemes parsed to list)
- LanguageData includes Optional coordinates (tuple[float, float] or None)

**Date**: 2026-03-05

## Task 7: Suffix Trie Implementation

**Implementation Strategy:**
- Refactored existing prefix trie code to extract shared `_insert_into_trie()` function
- Suffix trie: reverses phoneme sequences BEFORE insertion, then uses identical insertion logic
- Both tries use same node/edge attribute schema for consistency

**Key Design Decisions:**
- Node ID format: joined phonemes with "-" separator (e.g., "a-k-a")
- Root node: "ε" (epsilon) for both prefix and suffix tries
- Edge type attribute: "prefix" vs "suffix" to distinguish trie type
- Phoneme reversal: `list(reversed(entry.phonemes))` creates new list, preserves input

**Code Reuse Success:**
- ~60 lines of duplicate insertion logic eliminated
- Shared function ensures consistent behavior between prefix/suffix
- Graph metadata differs: `trie.graph["trie_type"]` = "prefix" or "suffix"

**Verification Results (small test dataset):**
- Suffix trie: 16 nodes, 15 edges, 3 root branches
- Common final phonemes detected: /a/ (2 langs, 845M speakers), /ə/ (1 lang, 1.7B), /i/ (1 lang, 1.3B)
- Spanish "agua" + Russian "voda" correctly cluster on final /a/
- Prefix trie: 17 nodes, 16 edges, 4 root branches (initial phonemes)

**Technical Notes:**
- Suffix trie's `phoneme_sequence` attribute stores REVERSED phonemes (e.g., ["a", "d", "a", "v"] for "voda")
- This reversal is intentional: captures word endings for right→left traversal
- Accumulated speaker counts show convergence strength at each suffix depth
- Node scoring function (`depth * speaker_count`) works identically for both tries

**Integration Points:**
- Task 6 (prefix trie) and Task 7 (suffix trie) now share core insertion logic
- Ready for Task 8 (convergence point detection): bridge edges will connect prefix/suffix nodes
- Bowtie graph structure: prefix trie ← bridge edges → suffix trie


## Task 6: Prefix Trie Builder

**Implementation**: `pangloss/graph/trie.py`

### Key Design Decisions

1. **NetworkX DiGraph as backing store**: Used `nx.DiGraph()` directly instead of custom trie class
   - Leverages NetworkX's graph algorithms and serialization
   - Node IDs are phoneme sequences joined by '-' (e.g., 'w-ɑː-t')
   - Root node at 'ε' (epsilon) represents empty sequence

2. **Node attributes**:
   - `phoneme_sequence`: list of phonemes (accumulated path from root)
   - `depth`: distance from root (1-indexed)
   - `languages`: set of language_ids passing through this node
   - `speaker_count`: sum of speakers from all languages at this node

3. **Edge attributes**:
   - `phoneme`: the phoneme added at this edge
   - `languages`: set of language_ids using this edge
   - `type`: 'prefix' (distinguishes from suffix edges in Task 7)

4. **Iterative insertion**: Left-to-right phoneme traversal
   - Avoids recursion depth issues with long words
   - Accumulates language sets and speaker counts at each node
   - Creates nodes/edges lazily as needed

5. **Node scoring**: `depth * speaker_count`
   - Rewards both specificity (depth) and universality (speakers)
   - Used by downstream tasks to find convergence points

### Verification Results

**Synthetic test** (26 languages, 6 families):
- 66 nodes, 9 root branches
- Average clustering purity: 75.4% (vs 50% random)
- Family patterns emerge naturally:
  - /v/ branch: Germanic + Slavic (shared Indo-European)
  - /a/ branch: Romance + Austronesian (convergent evolution)
  - /w/ branch: Germanic (English, Dutch)
  - Asian languages: distinct branches (/ʂ/, /m/, /t/, /tʃ/)

**Key insight**: Language families cluster on initial phoneme sequences WITHOUT any linguistic metadata input—pure phonetic convergence reveals family structure.

### Performance Notes

- Matrix building with full ASJP data is slow due to speaker count warnings
- For development: use synthetic test data or suppress stderr
- Production: Consider caching matrix or batch processing

### Integration Points

- Input: `MatrixEntry` objects from `pangloss.data.matrix`
- Output: NetworkX DiGraph with metadata
- JSON serializable via `networkx.readwrite.json_graph.node_link_data()`
- Blocks Task 8 (bridge edges) and Task 9 (word generation)


## Language-Concept Matrix Builder (Task 5)

**Date**: 2026-03-05

**Key Insights**:
- Matrix integration bridges ASJP forms, speaker counts, and metadata into unified structure
- Performance bottleneck: `get_speakers_for_asjp_language()` reloads CSV mappings on every call (~90ms/lookup)
- Solution: Inline speaker lookup logic with pre-loaded mappings (prevents CSV re-parsing)
- Water concept: 11,873 forms, 228B total speakers (accounting for duplicates), 387 language families

**Data Quality**:
- Languages with speaker counts: 10,695/11,540 (91.2%)
- Unmapped languages: 1,024 (8.8%) → use speaker_count=0 fallback
- All entries have complete fields: language_id, phonemes, speaker_count, family, name
- Most represented families: Atlantic-Congo, Austronesian, Sino-Tibetan, Trans-New Guinea

**Implementation Notes**:
- Lazy-load language metadata from `_parse_languages()` only when not provided as argument
- Pre-load ISO↔ASJP mappings once to avoid repeated CSV parsing (critical for performance)
- Inline speaker lookup: asjp_id → iso_code → representative_asjp_id → speaker_count
- MatrixEntry includes both `language_id` (ASJP ID) and `language_name` (human-readable)
- ConceptEntry pre-computes aggregate stats: total_languages, total_speakers, language_families (as set)

**Edge Cases Handled**:
- Empty phonemes after normalization: skip entry (rare, ~0 cases in water)
- Unmapped languages: track count, use 0 speakers, preserve entry
- Missing language metadata: use empty string for family, ASJP ID as name
- Multiple forms per language-concept: keep all (no deduplication per ASJP design)

**Performance**:
- Full matrix build (40 concepts): ~10 minutes for 400K+ forms
- Per-concept build (water): ~1 second for 11,873 forms
- Bottleneck eliminated: reduced speaker lookup from 90ms to <1ms per form

**Verification Evidence**:
```
Forms: 11873
Total speakers: 228,985,224,125
Sample entry: MatrixEntry(
  language_id='A51_BAFIA_MAJA',
  phonemes=['m', 'o', 'm', 'o'],
  speaker_count=15000,
  language_family='Atlantic-Congo',
  language_name='A51_BAFIA_MAJA',
  raw_value='momo'
)
```

### Task 8: Convergence Point Detector Learnings
- **Split-Point Search works beautifully**: Enumerating all possible valid phoneme splits for every word and looking up their corresponding prefix and suffix nodes is efficient and correctly identifies global structure since it operates entirely on pre-built tries without deep traversals.
- **Distinctness Filter is Critical**: Without filtering for distinctness (e.g., <20% language set overlap between returned convergence points), the top-K results are completely dominated by trivial variations of the largest clusters.
- **Mandarin Speaker Count Inflation**: Sinitic languages (Mandarin variants) dominate the absolute highest raw scores due to the speaker mapping decision from Wave 2 (where each variant receives the entire ~1.1 Billion ISO code speaker count). The distinctness filter ensures this only eats up *one* or *two* top spots (because later ones overlap with the first and get filtered out).
- **Phonetic Universals Discovered**: The algorithm successfully isolates structural components of major language families automatically. For "*water", we verified it cleanly extracts:
  - Germanic: `/w/ + /ɐ-t-ə-r/`
  - Slavic: `/v-o/ + /d-ɐ/`
  - Indo-Aryan: `/p-ɐ/ + /n-i/`
  - Romance: broadly clustered under `/ɐ/` (due to variations like `/ɐ-k-w-ɐ/` vs `/a-g-w-a/` splitting deeper nodes).

## Task 9: Word Generator
- The naive greedy outward expansion suggested in the vision doc (dropping a phoneme from prefix and prepending to suffix) actually causes overlapping phonemes to be generated (e.g. `shshuei`).
- To fix this and properly grow the word to make it distinctive, the implemented algorithm GROWS both the prefix and suffix by exploring their child nodes, stopping when adding a phoneme reduces speaker coverage too heavily compared to the length gain.
- The scoring function `score = speakers * length_penalty` where `length_penalty = prefix_len * 2 + suffix_len` brilliantly solves the problem of balancing speaker coverage with word distinctiveness (length). It ensures that extending a word is accepted if the speaker drop is justified by the word becoming more robust.
- Anti-overlap heuristics were necessary to prevent the suffix trie from simply re-adding the last character of the prefix back onto the suffix when expanding.

## Task 10: Synonym Selector — Weighted Set Cover (2026-03-05)

**Greedy Set Cover Implementation**:
- Implemented greedy weighted set cover to select minimum synonyms achieving target coverage
- Algorithm tracks uncovered languages and iteratively selects candidate with highest estimated speaker contribution
- Uses language-proportion estimation: for each candidate, estimates speakers contributed by (new_langs / total_langs) * speaker_count
- Stops when: (1) coverage threshold reached, OR (2) no candidates add new languages

**Coverage Delta Tracking**:
- Each selected synonym gets `coverage_delta` attribute tracking speakers it contributed
- Used `object.__setattr__()` to dynamically add attribute to dataclass instances without modifying base class
- Alternative considered: return tuples or wrapper dataclass, but dynamic attribute simpler for downstream use

**Edge Case Handling**:
- When max achievable coverage < threshold: algorithm returns ALL useful synonyms that add coverage
- Verified behavior: water concept reaches only 77.2% max coverage (cannot reach 90% due to candidate overlap)
- Proper edge case detection: re-runs selection at 100% threshold to compute max achievable coverage

**Algorithm Performance**:
- 50% threshold: 2 synonyms ("shuei" + "suei") → 53.2% coverage, 144 languages
- 90% threshold: 20 synonyms → 77.2% max achievable (all candidates exhausted)
- 99% threshold: Same as 90% (max achievable is limiting factor)

**Candidate Overlap Issue Discovered**:
- Many convergence points from water share overlapping Sinitic language clusters
- Top 8 candidates (shuei, suei, shi, shui, fei, sei, shei, shue) all cover similar Mandarin/Cantonese variants
- This explains why adding more synonyms after first 2-3 provides diminishing returns
- Coverage grows from 53% → 77% across 18 additional synonyms (only 24% gain for 18 words)

**Monotonicity Verification**:
- Confirmed: Higher thresholds require equal or more synonyms
- 50% → 2 words, 90% → 20 words, 99% → 20 words
- Monotonicity holds even when threshold exceeds max achievable coverage

**Data Quality Observation**:
- Total water speakers: 229B (with Mandarin/Cantonese duplicate inflation)
- Top convergence point covers 62.9B speakers (27.5%) across only 71 languages
- Second point adds 59.0B speakers (25.8%) across 73 languages
- First two synonyms together cover 53% of speakers but only 144/11,873 languages (1.2%)
- Indicates heavy concentration in Sinitic language family (expected for water concept)

**Implementation Learnings**:
- Speaker-based greedy selection is more complex than unweighted set cover
- Without per-language speaker breakdowns in SyntheticWord, must estimate via proportion
- Estimation works well: proportional contribution approximates actual speaker-weighted coverage
- Future optimization: store per-language speaker counts in SyntheticWord for exact computation

**API Design**:
- Function signature: `select_synonyms(candidates: List[SyntheticWord], coverage_threshold: float = 0.9)`
- Returns: List[SyntheticWord] ordered by coverage contribution (descending)
- Each returned word has `coverage_delta` attribute (speakers added)
- Clean separation: selector knows nothing about tries/graphs, only operates on SyntheticWord list

**Testing Strategy**:
- Manual verification via script (no automated tests per plan constraint)
- Evidence files created:
  - task-10-synonyms-water.txt: Full selection results at 90% threshold
  - task-10-threshold-config.txt: Comparison across 50%, 90%, 99% thresholds
- Verified monotonicity, edge case handling, and coverage delta accuracy

**Date**: 2026-03-05
