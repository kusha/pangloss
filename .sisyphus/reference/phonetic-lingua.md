# Phonetic Lingua: A Data-Driven Synthetic Language Generator

## Vision

Build a synthetic vocabulary optimized for **maximum cross-language recognition** by native speakers. Instead of one person designing a constructed language (like Esperanto), this system empirically discovers the most universally recognizable phonetic forms for each concept by analyzing real pronunciations across 25+ languages.

The key insight: **2–3 synonyms per concept can achieve near-universal intuitive recognition**, where each synonym targets a different language family cluster.

---

## Core Concept

For any concept (e.g. "water"):

1. Translate it into 25+ languages
2. Convert each translation to IPA (phonetic) representation
3. Build a **prefix/suffix graph** that reveals shared phonetic patterns
4. Extract the "fattest" branches — phoneme sequences shared by the most languages
5. Combine fat prefixes × fat suffixes to generate candidate synthetic words
6. Select 1–3 synonyms that together cover the maximum number of speakers

### Example Output

```yaml
concept: "water"
words:
  - form: "aka"
    ipa: /aka/
    covers: [es, pt, it, fr, ro, tr, ja, ...]   # ~2B speakers
    source_pattern: Latin "aqua" family
  - form: "voda"
    ipa: /voda/
    covers: [ru, uk, pl, cs, bg, sr, hr]         # ~300M speakers
    source_pattern: Slavic "voda" family
  - form: "watr"
    ipa: /watɹ/
    covers: [en, de, nl, da]                     # ~600M speakers
    source_pattern: Germanic "water" family
```

---

## The Graph: Prefix-Suffix Bowtie

### Structure

The graph has an hourglass / bowtie shape:

```
       PREFIX TRIE (left→right)         SUFFIX TRIE (right←left)

  ε ─→ /k/ ─→ /ka/ ─→ /kas/ ──╮    ╭── /a/ ←── /wa/ ←── ε
                                │    │
  ε ─→ /v/ ─→ /vo/ ───────────╮├────┤╭── /da/ ←── /oda/ ←── ε
                                ││    ││
  ε ─→ /w/ ─→ /wa/ ───────────╯│    │╰── /tɹ/ ←── /atɹ/ ←── ε
                                │    │
  ε ─→ /m/ ─→ /mi/ ───────────╯    ╰── /zu/ ←── /izu/ ←── ε

                        BRIDGE EDGES
                   (one per language path)
```

### Node Types

| Type | Description | Direction |
|------|-------------|-----------|
| **Prefix node** | Phoneme sequence from word start | left → right |
| **Suffix node** | Phoneme sequence from word end | right → left |
| **Bridge edge** | Connects a language's deepest prefix to its deepest suffix | middle |

### Properties Per Node

```
Node {
  id: string                  // unique identifier
  type: "prefix" | "suffix"
  phonemes: string            // accumulated phoneme sequence (e.g. "/ka/")
  depth: int                  // distance from root
  languages: Set<string>      // which languages pass through this node
  speaker_count: int          // total native speakers of languages in set
}
```

### Properties Per Edge

```
Edge {
  from: node_id
  to: node_id
  type: "trie" | "bridge"
  languages: Set<string>
  weight: int                 // |languages| or speaker_count
}
```

### Why This Shape

- **Prefix trie** captures shared word beginnings → reveals etymological families (Romance langs share Latin roots, Slavic langs share Proto-Slavic roots)
- **Suffix trie** captures shared word endings → reveals morphological patterns (many languages end words in vowels, or in common suffixes)
- **Bridge edges** represent each language's unique middle portion
- **Fat branches** (high `|languages|`) are the phonetic universals — the building blocks of the synthetic vocabulary
- Language families **emerge naturally** from the graph without any linguistic taxonomy as input

---

## Algorithm

### Pipeline

```
┌──────────────┐     ┌────────────┐     ┌──────────────────┐
│ 1. Translate  │────▶│ 2. IPA     │────▶│ 3. Prefix/Suffix │
│ (25+ langs)   │     │ Convert    │     │ Graph Builder     │
└──────────────┘     └────────────┘     └────────┬─────────┘
                                                  │
                                                  ▼
                                        ┌──────────────────┐
                                        │ 4. Fat Branch     │
                                        │ Extractor         │
                                        └────────┬─────────┘
                                                  │
                                                  ▼
                                        ┌──────────────────┐
                                        │ 5. Synonym        │
                                        │ Selector          │
                                        └────────┬─────────┘
                                                  │
                                                  ▼
                                        ┌──────────────────┐
                                        │ 6. Output         │
                                        │ Synthetic Word(s) │
                                        └──────────────────┘
```

### Step 1: Translation

Translate the source concept into 25+ target languages. Suggested set:

| Family | Languages |
|--------|-----------|
| Germanic | English, German, Dutch, Swedish, Danish |
| Romance | Spanish, Portuguese, French, Italian, Romanian |
| Slavic | Russian, Polish, Czech, Ukrainian, Bulgarian, Serbian, Croatian |
| Indo-Iranian | Hindi, Urdu, Persian, Bengali |
| Sino-Tibetan | Mandarin Chinese |
| Japonic | Japanese |
| Koreanic | Korean |
| Turkic | Turkish |
| Semitic | Arabic, Hebrew |
| Austronesian | Indonesian, Tagalog |
| Dravidian | Tamil, Telugu |
| Bantu | Swahili |
| Tai-Kadai | Thai |
| Austroasiatic | Vietnamese |

Tools: Google Translate API, LibreTranslate, or a curated dictionary (Wiktionary).

### Step 2: IPA Conversion

Convert each translation to its IPA phonetic representation.

Tools:
- **espeak-ng**: good coverage, CLI-based, works for most European languages
- **epitran**: Python library, grapheme-to-phoneme for many languages
- **Wiktionary**: has IPA for most common words (can be scraped)

Caveats:
- Tonal languages (Mandarin, Thai, Vietnamese): strip tones for substring matching, but preserve them in output
- Transliterated languages (Japanese, Chinese): use standard romanization IPA

### Step 3: Build Prefix/Suffix Graph

```python
def build_prefix_trie(ipa_strings: dict[str, str]) -> Trie:
    """Build trie from IPA strings, phoneme by phoneme, left to right."""
    trie = Trie()
    for lang, ipa in ipa_strings.items():
        phonemes = segment_into_phonemes(ipa)
        trie.insert(phonemes, lang)
    return trie

def build_suffix_trie(ipa_strings: dict[str, str]) -> Trie:
    """Build trie from reversed IPA strings (right to left)."""
    trie = Trie()
    for lang, ipa in ipa_strings.items():
        phonemes = list(reversed(segment_into_phonemes(ipa)))
        trie.insert(phonemes, lang)
    return trie
```

Key detail: **segment into phonemes**, not characters. IPA characters like `/tʃ/`, `/aː/`, `/dʒ/` are single phonemes but multiple Unicode characters. Use a phoneme segmentation library or regex.

### Step 4: Fat Branch Extraction

Traverse each trie and score every node:

```python
def score_node(node):
    """Score = how valuable this phoneme sequence is as a word fragment."""
    return node.depth * node.speaker_count

def extract_fat_branches(trie, min_languages=3):
    """Return nodes where many languages converge."""
    candidates = []
    for node in trie.dfs():
        if len(node.languages) >= min_languages:
            candidates.append((node, score_node(node)))
    return sorted(candidates, key=lambda x: -x[1])
```

### Step 5: Synonym Selection (Weighted Set Cover)

```python
def select_synonyms(prefix_branches, suffix_branches, max_synonyms=3):
    """
    Greedy weighted set cover:
    1. Generate all prefix × suffix combinations
    2. Score each by total speaker coverage
    3. Greedily pick combos that maximize uncovered speakers
    """
    uncovered = set(all_languages)
    synonyms = []

    while uncovered and len(synonyms) < max_synonyms:
        best_combo = None
        best_score = 0

        for prefix in prefix_branches:
            for suffix in suffix_branches:
                covered = (prefix.languages & suffix.languages) & uncovered
                score = sum(speaker_count[l] for l in covered)
                if score > best_score:
                    best_score = score
                    best_combo = (prefix, suffix, covered)

        if best_combo:
            prefix, suffix, covered = best_combo
            word = combine(prefix.phonemes, suffix.phonemes)
            synonyms.append({
                'form': ipa_to_spelling(word),
                'ipa': word,
                'covers': covered
            })
            uncovered -= covered

    return synonyms
```

### Step 6: Output

For each concept, output:
- The synthetic word(s) with IPA
- Which languages each synonym covers
- Speaker count coverage
- The graph visualization

---

## Scoring: Recognition Score

Not all phoneme matches are equal. A more sophisticated scoring model:

```python
def recognition_score(synthetic_ipa, native_ipa):
    """
    How likely a native speaker of language L would recognize the synthetic word.

    Factors:
    - Shared prefix length (strong cue — word-initial sounds are most salient)
    - Shared suffix length (weaker but still helpful)
    - Overall phoneme overlap
    - Phonetic distance for near-misses (/k/ vs /g/, /p/ vs /b/)
    """
    prefix_match = common_prefix_length(synthetic_ipa, native_ipa)
    suffix_match = common_suffix_length(synthetic_ipa, native_ipa)
    # Prefix weighted 2x because word-initial recognition is stronger
    return (2 * prefix_match + suffix_match) / (2 * len(native_ipa) + len(native_ipa))
```

### Phonetic Distance (Future Enhancement)

Instead of exact phoneme matching, use feature-based similarity:

| Phoneme pair | Distance | Reason |
|---|---|---|
| /k/ — /k/ | 0.0 | identical |
| /k/ — /g/ | 0.1 | same place, voicing differs |
| /k/ — /t/ | 0.3 | same manner, place differs |
| /k/ — /s/ | 0.7 | different manner and continuancy |
| /k/ — /a/ | 1.0 | consonant vs vowel |

This would let "aka" partially match "aga" (voiced variant), expanding coverage.

---

## Practical Applications

1. **Universal signage vocabulary** — a small set of words recognizable across language barriers (airports, emergencies)
2. **Brand naming** — create product names that "feel right" in the most markets
3. **Emergency communication** — a 50-word survival vocabulary with near-universal recognition
4. **Language learning bridge** — use as a stepping stone vocabulary for polyglot learners
5. **Research** — quantify phonetic universals and language family clustering

---

## Suggested Starter Vocabulary (Swadesh-like Core List)

Test the system with these high-value concepts first:

| Category | Concepts |
|----------|----------|
| Elements | water, fire, sun, moon, earth, sky |
| People | mother, father, child, person, friend |
| Body | hand, eye, head, heart, blood |
| Actions | eat, drink, sleep, go, come, give, see |
| Qualities | big, small, good, bad, new, old |
| Numbers | one, two, three, five, ten |
| Basics | yes, no, name, house, food |

---

## Tech Stack Recommendations

| Component | Option A (Quick) | Option B (Production) |
|-----------|-------------------|----------------------|
| Translation | Hardcoded Wiktionary data | Google Cloud Translate API |
| IPA conversion | espeak-ng CLI | epitran + Wiktionary scraper |
| Graph building | Python networkx | Rust petgraph (performance) |
| Visualization | graphviz DOT | D3.js interactive web app |
| Storage | JSON files | SQLite or PostgreSQL |
| Language | Python 3.11+ | Python + Rust core |

### Minimum Viable Prototype

```
Python 3.11+ with:
- networkx (graph)
- epitran or espeak-ng (IPA)
- graphviz (visualization)
- a JSON dict of {concept: {lang: translation}} for 10 concepts × 25 langs
```

---

## Open Questions / Future Directions

- **Phonotactic constraints**: The synthetic words should be pronounceable. Filter candidates through phonotactic rules (no /ŋr/ clusters, etc.)
- **Collision avoidance**: Ensure different concepts don't produce identical or near-identical synthetic words
- **Tone/stress**: How to handle tonal language data? Probably strip for matching, preserve in output
- **Morphology**: Could the prefix/suffix system extend to generate compound words? (e.g., "firewater" from "fire" + "water" synthetic forms)
- **Weighting strategy**: speaker count vs. geographic spread vs. language family diversity — which matters more?
- **Perceptual validation**: ultimately, test with human subjects — does "aka" actually make Hindi/Turkish/Japanese speakers think "water"?
