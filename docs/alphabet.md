# Pangloss Canonical Alphabet

This document describes the **reduced canonical alphabet** used by Pangloss
to write synthetic word forms. It is deliberately simplified: we trade
IPA precision for cross-family recognizability and short, typable forms.

> **Scope**: This describes the OUTPUT orthography (the `form` field in
> `dictionary.json`). The INPUT data (ASJP phonetic transcriptions) retains
> full phonemic detail; canonicalization happens only at the final
> transliteration step.
>
> **Source of truth**: `pangloss/data/phonemes.py` — `CANONICAL_PHONEME` dict.
> This document must be regenerated / reviewed when that dict changes.

---

## TL;DR

- **23 graphemes total**: 18 consonants + 5 vowels.
- **17 single-letter** + **3 digraphs** (`sh`, `ch`, `ng`).
- All using **plain ASCII lowercase latin** — no diacritics, no IPA symbols.
- Voicing is **collapsed** (t=d, p=b, k=g, f=v, s=z). We keep only the
  voiceless representative for stops/fricatives.
- Vowel space is collapsed to **5 vowels** (a, e, i, o, u) — Spanish/Japanese-like.
- **Labial merger**: `v`, `w`, `ʋ`, `β` all written as `w`.

---

## The Alphabet

### Vowels (5)

| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `a` | /a, ɑ, ɐ, ʌ, ə, ɘ, ɵ, ɜ/ | open/central any quality |
| `e` | /e, ɛ, æ, ø, œ/ | mid-front any rounding |
| `i` | /i, ɪ, y, ɨ/ | high-front any rounding |
| `o` | /o, ɔ, ɒ, ɤ/ | mid/low back rounded |
| `u` | /u, ʊ, ʉ/ | high-back any rounding |

### Consonants (18)

#### Stops (3) — voicing collapsed
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `p` | /p, b/ | any bilabial stop |
| `t` | /t, d, θ, ð/ | any alveolar/dental stop or fricative |
| `k` | /k, ɡ, q/ | any velar/uvular stop |

#### Fricatives (4)
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `f` | /f/ | voiceless labiodental fricative |
| `s` | /s, z, ts, dz/ | any alveolar sibilant/affricate |
| `sh` | /ʃ, ʒ, ʂ, ʐ, ç, ʝ/ | any post-alveolar/palatal sibilant |
| `h` | /h, ɦ, x, ɣ, χ/ | any glottal/velar/uvular fricative |

#### Affricate (1)
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `ch` | /tʃ, dʒ/ | any post-alveolar affricate |

#### Nasals (3)
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `m` | /m/ | bilabial nasal |
| `n` | /n, ɲ, ɳ/ | any coronal/palatal nasal |
| `ng` | /ŋ/ | velar nasal |

#### Liquids (2)
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `l` | /l, ʎ, ɭ/ | any lateral |
| `r` | /r, ɾ, ɹ, ʀ, ʁ, ɽ/ | any rhotic (trilled, tapped, approximant) |

#### Approximants (2)
| Grapheme | Represents (IPA) | Pronounce as |
|---|---|---|
| `w` | /w, v, ʋ, β, ɰ/ | any labial/labiodental approximant or fricative |
| `y` | /j/ | palatal approximant |

#### Dropped entirely
- `ʔ` (glottal stop) — silent
- Length markers `ː`, aspiration `ʰ`, labialization `ʷ`, palatalization `ʲ`,
  pharyngealization `ˤ`, nasalization ` ̃`, stress `ˈ`, `ˌ` — all stripped.

---

## Frequency in Generated Lexicon

Measured on the current 40-concept lexicon (128 synonyms, 861 grapheme
occurrences):

| Rank | Grapheme | Count | % |
|---:|---|---:|---:|
| 1 | a | 163 | 18.9% |
| 2 | i | 111 | 12.9% |
| 3 | n | 76 | 8.8% |
| 4 | m | 63 | 7.3% |
| 5 | u | 61 | 7.1% |
| 6 | o | 56 | 6.5% |
| 7 | t | 56 | 6.5% |
| 8 | k | 54 | 6.3% |
| 9 | s | 43 | 5.0% |
| 10 | e | 29 | 3.4% |
| 11 | l | 25 | 2.9% |
| 12 | r | 24 | 2.8% |
| 13 | p | 21 | 2.4% |
| 14 | h | 19 | 2.2% |
| 15 | y | 18 | 2.1% |
| 16 | w | 15 | 1.7% |
| 17 | ch | 15 | 1.7% |
| 18 | f | 5 | 0.6% |
| 19 | sh | 4 | 0.5% |
| 20 | ng | 3 | 0.3% |

**Vowels total: ~48.8%** of all graphemes — consistent with a Spanish/Japanese-style open syllabary.

**Rare graphemes** (`f`, `sh`, `ng` each < 1%) — consider whether this
underrepresentation is a bug (source data truly lacks them) or an artifact
of the canonicalization rules. See Known Limitations.

---

## Design Rationale

### Why collapse voicing?
Voicing oppositions (`/t/` vs `/d/`) exist in many languages but are
allophonic or contextual in many others (Mandarin, Korean, Japanese don't
phonemically distinguish `/d/` and `/t/` initially). Keeping both doubles
the alphabet with minimal recognition gain.

### Why 5 vowels?
5-vowel systems (`a e i o u`) are the single most common vowel inventory
worldwide (~30% of languages in UPSID). Any vowel a speaker pronounces
will be mapped to the nearest of the 5 and remain recognizable. 7, 9, 12
vowel systems increase precision but at the cost of learnability for the
majority.

### Why labial merger (v = w)?
Languages that have `/v/` (Russian, English, French) and languages that
have `/w/` (Spanish, English, Japanese) rarely have BOTH as phonemic
contrasts in everyday vocabulary. Treating them as one lets `wota` (water)
be heard as `/voda/`, `/wata/`, `/βoθa/` without losing the cluster.

### Why no tone, no length, no stress?
Most of the world's speakers do not use tone phonemically. Vowel length
is phonemic in ~20% of languages. Stress is predictable or absent in
many. Including any of them would either:
- force speakers of non-tonal/non-length languages to ignore diacritics
  (then why write them?), OR
- exclude languages that don't have the feature.

### Why ASCII latin?
- Typable on every keyboard on Earth.
- Renders correctly in every font.
- No Unicode normalization issues.
- The latin script has already won for code, URLs, email, and
  international transliteration of proper nouns.

### Why digraphs for sh, ch, ng?
They're the three consonant categories that couldn't be collapsed into a
single-letter slot without losing phonemic identity in most of the
world's languages. Using digraphs keeps the alphabet pure ASCII. Every
major romanization convention (pinyin, Hepburn, Polish) already uses
these digraphs, so they're widely recognized.

---

## How to Read a Pangloss Form

When you see `wota`:

1. Start with the canonical alphabet map.
2. Each grapheme is a **tolerance class**, not an exact sound.
3. Your native phonology will naturally pick the nearest phoneme:
   - Russian speaker reads `w` as `[v]`, `o` as `[o]`, `t` as `[t]`, `a` as `[a]` → `/voda/` (вода)
   - English speaker reads `w` as `[w]`, `o` as `[ɔ]`, `t` as `[t]`, `a` as `[ə]` → `/wɔtə/`
   - Spanish speaker reads `w` as `[β]`, `o` as `[o]`, `t` as `[t]`, `a` as `[a]` → `/βota/`
4. All three are "correct" readings.

This is the point: **one written form, many spoken forms, all mutually
recognizable as the same word.**

---

## Known Limitations

1. **No explicit orthographic rules**: no capitalization, punctuation, or
   word-boundary guidance. The alphabet defines graphemes, not a writing
   system.

2. **Low frequency of `f`, `sh`, `ng`**: these graphemes appear rarely in
   the current lexicon. Possible causes:
   - ASJP source data underrepresents them.
   - Canonicalization over-collapses (e.g., `/ʃ/` → `sh` is the only path in,
     but many sh-like sounds in ASJP may arrive as `s` instead).
   - Not enough concepts yet (n=40) to see long-tail graphemes.

3. **No distinction between the short-vowel classes** (`a` and `ə` both
   render as `a`). Some languages rely on schwa for grammatical purposes;
   Pangloss ignores this.

4. **Digraph ambiguity**: `sh` could in principle be parsed as `s` + `h`.
   In practice `s+h` never occurs as an adjacent pair in generated forms,
   so this is safe — but the lexer assumes digraph-first greedy matching.

5. **Not fully reversible**: given a Pangloss form, you CANNOT reconstruct
   the original IPA. This is intentional (many-to-one mapping).

---

## When This Document Should Be Updated

- Any change to `CANONICAL_PHONEME` in `pangloss/data/phonemes.py`.
- Any change to the set of "dropped" phonemes.
- When adding/removing graphemes.
- When the lexicon is regenerated and frequency table shifts by >2
  percentage points on any grapheme.

A short script can regenerate the frequency table from
`output/dictionary.json`:

```bash
source .venv/bin/activate
python3 -c "
import json, re
from collections import Counter
d = json.load(open('output/dictionary.json'))
forms = [s['form'] for c in d['concepts'] for s in c['synonyms']]
g = re.compile(r'sh|ch|ng|[a-z]')
counter = Counter()
for f in forms: counter.update(g.findall(f))
total = sum(counter.values())
for g, n in counter.most_common():
    print(f'| {g} | {n} | {100*n/total:.1f}% |')
"
```

---

*Last regenerated: 2026-04-19 (lexicon of 40 concepts / 128 synonyms).*
