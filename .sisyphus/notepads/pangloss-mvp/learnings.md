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

