# Pangloss v3: Zipf-ordered Lexicon — Short Forms for Frequent Concepts

> **⚠ BLOCKED BY v2.5 (Inspection Web UI) — see section at the end of this file.**
> Before any Zipf-length work, the generation pipeline must be debuggable
> visually per-concept. Current lexicon audit (2026-04-19) revealed
> systemic issues (33/40 concepts have only 1 synonym, 36/40 have total
> coverage < 50%, near-dupe pairs confirmed) that cannot be triaged from
> table dumps alone. v3 resumes only after v2.5 ships and the generation
> pipeline is "finalized" (see v2.5 scope).

## TL;DR

> **Quick Summary**: Reorient synonym generation from per-concept independent optimization to **whole-lexicon co-optimization**. Frequent concepts (e.g., "water", "eye") should get SHORT forms; rare concepts can afford LONGER forms. Short forms are a scarce shared resource — allocate them by concept frequency, while guarding against within-language homonym collisions.
>
> **Core Insight (from user)**: "If creating a language, short forms should go first to frequently used words."
>
> **Deliverables**:
> - Concept frequency ranking (Zipf order) from external frequency source
> - Length budget allocated per concept based on frequency rank
> - Selector prefers shortest sufficient form when coverage-equivalent alternatives exist
> - Redundancy suppression: drop longer variants that share a root with an already-selected shorter form, UNLESS the longer form uniquely rescues coverage
> - Cross-concept homonym guard: a short form claimed by concept A is blocked (or penalized) for concept B
> - New CLI knobs and evidence-based evaluation
>
> **Estimated Effort**: Medium-Large
> **Parallel Execution**: Partial — frequency source (T1) blocks allocator (T3); collision guard (T5) depends on allocator
> **Critical Path**: T1 frequency source → T2 redundancy metric → T3 length budget → T4 selector rewrite → T5 cross-concept homonym guard → T6 CLI + evidence

---

## Context

### Original Request (verbatim-ish)

> Почему 1 и 2 [`wota` и `wotar`] так схожи? Я думаю если это разница лишь в префиксе или суффиксе то короткое слово лучше длинного. Но только если не будет конфликта с другими словами в языке. Поэтому должна быть генерация словаря в частотном порядке.
>
> Clarification: "Если создавать язык то короткие формы должны занять в первую очередь слова с частым употреблением".

### Concrete Motivating Example

For `*water` the v2 pipeline produced (in this order):

| # | form  | cov%  | langs |
|---|-------|-------|-------|
| 1 | wota  | 20.41 | 37 (Slavic + some Germanic) |
| 2 | wotar | 17.59 | 7  (English, Scots, Dutch_2, Swedish_2, Gronings, Sallands) |

Observations:
- `wotar` is literally `wota + r` — same stem, longer suffix.
- Covered-language sets are **disjoint** (Slavic /voda/ vs Germanic /wɔtə(r)/), so current greedy set-cover correctly adds `wotar` for +7 languages.
- **But**: if "water" is a HIGH-frequency concept, the language designer would want `wota` as the canonical short form and accept that English speakers approximate via `wota` (perception is graded, not binary). Longer variants like `wotar` become affordable only for RARE concepts.
- Conversely, for a rare concept (e.g., `*louse`), going to 7–8 phonemes is fine because nobody says it 100× per day.

### Current State (v2 baseline)

- `selector.py`: greedy weighted set cover, maximizes speakers-per-step. No length penalty **at selection time**.
- `generator.py`: has a length penalty inside word scoring (`speakers / (1 + 0.5 * length)`), but it's per-candidate, not lexicon-aware.
- Coverage is computed **per concept, independently**. No notion that "water" should be cheaper to say than "louse".
- No check whether a form claimed for concept A collides with a form claimed for concept B inside the same real language (partial: `collisions.py` reports, does not act).

### Assumptions to Validate Before Coding

1. **Frequency source**: Do we use Swadesh-list ordering? Zipf by external corpus (Google Books, OpenSubtitles)? Uniform assumption "Swadesh = all high-frequency"?
2. **Redundancy definition**: When are two forms "the same root + affix"? Shared stem length ≥ N? Edit distance ≤ K with one side being a prefix/suffix of the other?
3. **Homonym guard scope**: block ALL within-language collisions, or only if both concepts are above a frequency threshold?
4. **Trade-off curve**: how aggressively do we sacrifice coverage for brevity? Is it a hard length cap per frequency rank, or a soft penalty in the objective?

→ **These will be resolved during T0 (Interview) before implementation.**

### Out of Scope (explicit)

- Phonotactics / syllable structure beyond current fuzzy matching.
- Morphological productivity (compounding, derivation) — v3 still emits atomic forms.
- Tone, stress, prosody.
- Changing the underlying ASJP data or phoneme model.

---

## Language Design Principles (user-stated, binding)

These are axioms for Pangloss as a constructed language. They constrain
every algorithm decision downstream and take precedence over local
optimizations.

### P1 — One grapheme, one sound. As written, so pronounced.
No silent letters. No context-dependent pronunciation. No digraph
ambiguity beyond the three fixed ones (`sh`, `ch`, `ng`). The canonical
alphabet (see `docs/alphabet.md`) is the complete inventory; nothing is
added implicitly.

**Implication for v3+**: Any future orthographic change MUST preserve
grapheme-phoneme bijection. No homographs-with-different-pronunciations.

### P2 — Simplicity of writing is a first-class optimization target.
When two forms are coverage-equivalent, the **shorter** / **simpler** /
**more typable** one wins. "Simpler" means: fewer graphemes, more
common graphemes (see frequency table in `docs/alphabet.md`), no rare
digraphs when single letters suffice.

**Implication for v3+**: Selector tiebreakers must prefer shorter /
higher-frequency-grapheme forms. This is already implicit in Zipf
length allocation (T3-T4) but deserves explicit tiebreak logic.

### P3 — No homonyms. One word, one meaning.
A word form claimed for concept A is **forbidden** for concept B —
globally, across the whole lexicon. The language does not tolerate
"bank" (river) vs "bank" (money). This applies to the Pangloss-wide
lexicon, not to real source languages.

**Implication for v3+**: The cross-concept homonym guard (T5) upgrades
from "penalize" to **hard block** as the default policy. The
`--homonym-policy` flag's default changes from `penalize` to `block`.
Exact-form collisions across concepts are rejected unconditionally.

### P4 — Synonyms within one concept ARE allowed.
Multiple forms for the same meaning are fine (and already present in
v2 — concept `*water` has 10 synonyms). Users can pick the form that
fits their phonological comfort zone. This asymmetry with P3 is
intentional:
- **Many→one (homonymy)**: BAD — ambiguity in comprehension.
- **One→many (synonymy)**: OK — choice in production.

**Implication for v3+**: Do NOT collapse synonyms for the sake of
"one form per concept" minimalism. The Zipf-length allocation (T3)
applies to each synonym INDEPENDENTLY: the shortest synonym for a
frequent concept is what counts against the length budget; additional
synonyms may be longer.

---

## Work Objectives

### Core Objective

Produce a lexicon where **word length is inversely correlated with concept frequency**, while preserving the coverage gains of v2 and avoiding within-language homonym collisions on high-frequency concepts.

### Concrete Deliverables

1. **Frequency ranking module** — maps each of the 40 concepts to a frequency rank (1 = most frequent).
2. **Length budget function** — `max_length(rank) → int`, monotonically non-decreasing in rank.
3. **Redundancy detector** — given two candidate forms for the same concept, determine if one is a "bare stem" of the other.
4. **Frequency-aware selector** — processes concepts in frequency order, enforces length budget, suppresses redundant longer variants unless they rescue otherwise-unreachable languages.
5. **Cross-concept homonym guard** — tracks forms already claimed and, per language, prevents/penalizes duplicate claims from later (rarer) concepts.
6. **CLI knobs**: `--length-curve {strict,soft,off}`, `--frequency-source <file>`, `--homonym-policy {block,penalize,ignore}`.
7. **Evidence**: before/after lexicon dumps for 5 representative concepts (water, eye, sun, louse, knee) with length-vs-frequency plot.

### Success Criteria (measurable)

- For top-10 frequency-ranked concepts: **median synonym length ≤ 4 phonemes** (current baseline measured in T0).
- For bottom-10 frequency-ranked concepts: median synonym length allowed up to 8 phonemes (current max).
- Global coverage drop vs v2 ≤ 5 percentage points (from 72.14%). Brevity is a trade, but catastrophic regressions are not acceptable.
- Zero cross-concept homonym collisions within any single language for top-20 concepts (under `--homonym-policy block`).
- **Zero exact-form homonyms across the entire Pangloss lexicon** (per P3). If two concepts both select form `mana`, the lower-frequency concept must pick a different form.
- Synonym counts per concept must not decrease more than ~20% on average (per P4 — synonyms are allowed and valued).
- On the `water` example: `wotar` is DROPPED (or demoted) if `water` is in top-rank; test expectation documented.
- **Tiebreak determinism** (per P2): given two forms with identical (coverage, length), the one using higher-frequency graphemes wins; if still tied, lexicographic order.

### Must NOT Have

- No new runtime dependencies unless T1 absolutely requires an external frequency list (prefer bundling a static JSON).
- No changes to `graph/trie.py`, `data/asjp.py` core loading, `data/phonemes.py` feature groups.
- No regression of v2 bug fixes (concept name `*` handling, YAML filename, coverage dedup).
- No silent behavior change when `--length-curve off` is passed — that flag must reproduce v2 output byte-for-byte (or document exact diff).

---

## Tasks

> **Status convention**: `[ ]` pending, `[~]` in progress, `[x]` done. Each task has own MUST DO / MUST NOT DO / EVIDENCE section when implementation starts.

### T0 — Interview & Assumption Resolution  `[ ]`
Resolve the four open questions in "Assumptions to Validate". Produce a short `decisions.md` in `.sisyphus/notepads/pangloss-v3/` committing to:
- Frequency source
- Redundancy definition (formal)
- Homonym guard scope
- Length-vs-coverage trade-off shape

### T1 — Frequency Ranking Module  `[ ]`
Add `pangloss/data/frequency.py`:
- Load concept → rank mapping from chosen source.
- Expose `rank_of(concept: str) -> int`, `ordered_concepts() -> list[str]`.
- Bundled default ranking committed as `data/concept_frequency.json`.

### T2 — Redundancy Detector  `[ ]`
Add `pangloss/algo/redundancy.py`:
- `is_redundant_variant(short: SyntheticWord, long: SyntheticWord) -> bool`
- Formal definition agreed in T0 (proposed: `long.form.startswith(short.form) or long.form.endswith(short.form)` AND `len(long.form) - len(short.form) ≤ 3` AND Jaccard(covered_languages) ≥ 0.5).
- Unit tests on the `wota`/`wotar` case and 3 other hand-picked pairs.

### T3 — Length Budget Function  `[ ]`
Add `max_length_for_rank(rank, total_concepts, curve) -> int` in `pangloss/algo/frequency_budget.py`.
- `curve="strict"`: hard cap, e.g. `2 + floor(rank / 5)`.
- `curve="soft"`: soft multiplier applied in scoring, no hard cap.
- `curve="off"`: returns `max_word_length` CLI value (v2 behavior).

### T4 — Frequency-Aware Selector Rewrite  `[ ]`
Refactor `pangloss/algo/selector.py`:
- Accept `length_budget: int` parameter.
- Filter candidates exceeding budget BEFORE greedy loop.
- When two candidates have coverage sets A ⊇ B and `is_redundant_variant(B, A)` holds, prefer the shorter one UNLESS dropping the longer costs > X% coverage (X from T0).
- Preserve v2 behavior exactly when budget is `inf`.

### T5 — Cross-Concept Homonym Guard  `[ ]`
Add `pangloss/algo/homonyms.py`:
- Global registry: `(language_id, form) -> concept` AND global form registry `form -> concept` (P3: no homonyms across the Pangloss lexicon itself, independent of source languages).
- `cli.py` iterates concepts in frequency order (from T1).
- For each candidate, check both registries; default action is **hard block** (per P3). `--homonym-policy {block,penalize,ignore}` with default `block`.
- Synonyms within a single concept are NOT subject to the guard (per P4).
- Logs suppressed candidates to evidence file.

### T6 — CLI + Pipeline Integration  `[ ]`
- Add CLI flags: `--length-curve`, `--frequency-source`, `--homonym-policy`.
- Thread through pipeline.
- Update `output/dictionary.py` to include `rank`, `length_budget`, and suppression reasons in per-concept output.

### T7 — Evidence & Evaluation  `[ ]`
Run pipeline with and without v3 changes on full 40-concept set:
- Produce length-vs-rank scatter plot (text histogram acceptable).
- Global coverage delta report.
- Homonym collision count (should be 0 for top-20 under `block`).
- Specific before/after for: water, eye, sun, tooth, knee, louse.
- Save to `evidence/v3/`.

### F1–F4 — Verification Wave  `[ ]`
Mirror v2 verification structure: plan compliance, code quality, real QA, scope fidelity.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Frequency data source has different concept labels than ASJP (`*water` vs `water`) | Normalize with existing `lstrip("*").lower()` helper; validate 100% mapping in T1 acceptance. |
| Aggressive length cap tanks global coverage | `--length-curve soft` as default; `strict` only opt-in; hard floor of 3 phonemes regardless of rank. |
| Redundancy detector false positives drop useful variants | T2 unit tests + evidence dump of all suppressed pairs for manual review. |
| Homonym guard order-dependent (processing order changes output) | Deterministic: always process by (rank asc, concept_name asc) for tie-breaking. |
| "Short form perceived across language families" is an untested assumption | v3 does NOT claim to measure perception; it claims to ALLOCATE brevity by frequency. Document the limitation. |

---

## Open Questions (tracked → resolved in T0)

1. Frequency source? (Swadesh default order / external corpus / user-provided JSON)
2. Formal redundancy definition?
3. Homonym guard: block vs penalize, threshold?
4. Length-vs-coverage trade-off: strict cap or soft penalty?

---

## Notes for Future Self

- The `wota`/`wotar` example is the canonical regression test. If v3 still emits both for a top-frequency `water`, v3 has failed its core objective.
- Do NOT conflate this plan with "general algorithm improvements". Scope is SPECIFICALLY: Zipfian length allocation + homonym guard. Other ideas go to a separate v4.
- User has NOT yet greenlit implementation. This plan is a record of intent; execution begins only on explicit request.

---

# v2.5 — Inspection Web UI (BLOCKING PREREQUISITE)

## Why this exists (user rationale, 2026-04-19)

> "Либо можно сделать веб-интерфейс который бы позволял проверить любое
> слово и рисовал граф и финальное решение."
>
> Follow-up: **"Наверное это логичнее чтобы я мог хорошо протестить
> генерацию."** ← This is the PRIMARY purpose. The UI is the user's
> testing cockpit for the generation algorithm, not a presentation
> layer. Every design decision defers to "what does the user need to
> see to diagnose a bad synonym?"
>
> Follow-up: **"Нам ещё нужны фонемы очевидно для большего числа
> слов."** ← v2.5 also covers expanding the concept set beyond
> Swadesh-40 so that testing has enough data to reveal patterns,
> enough long-tail graphemes to validate the canonical alphabet, and
> enough concept pairs to reveal real homonym conflicts.
>
> Prior context: "Надо прежде чем идти в частотный и делать хоть какой-то
> словарь финализировать генерацию."

The current pipeline is a black box. Audit of the 40-concept lexicon
reveals systemic quality issues that cannot be diagnosed from JSON
dumps:

- 33/40 concepts produce only **1 synonym** (e.g., `*eye`→`ian+chin`,
  `*tooth`→`ia+shi`). The greedy selector stops after one pick — is it
  threshold behavior, or does no second candidate add coverage?
- 36/40 concepts have **total coverage < 50%** (e.g., `*come` at 9.7%).
  Is the ASJP data that fragmented, or is the selector quitting early?
- 43 synonyms are **≥ 8 graphemes long**, mostly concentrated in
  `*one` (e.g., `alam+i+lapisa`, `ipos+la+mwas`). Why does one concept
  become a junkyard of hybrids?
- 49 synonyms have **< 1% coverage** each — are they useful or noise?
- Confirmed near-dupes beyond `wota/wotar`: `wahat/wahatu`,
  `trinka/trinkan`. Pattern: trailing single consonant. Root cause?

None of these are answerable without **per-concept visual inspection**:
the bowtie graph, which candidates won vs lost at each selector step,
which languages each form covers and why.

## Scope

A local web tool (no deployment, no auth) that takes a concept name and
shows:

1. **Bowtie graph** — prefix trie on the left, suffix trie on the right,
   convergence points (clusters) in the middle. Node size ~ speaker
   count, node color ~ language family.
2. **Convergence point list** — all points the algorithm considered
   before `generator.py` ran. Sortable by score, speakers, languages.
3. **Candidate table** — all `SyntheticWord`s generated. Columns:
   form, IPA, length, languages covered, speakers, selector score,
   **selected? (yes/no + reason if no)**.
4. **Selector trace** — step-by-step log: what was picked, what was
   rejected, current coverage after each step, why the loop stopped.
5. **Source forms panel** — for a given synonym, show the actual ASJP
   forms it claims to cover (so the user can verify `wota` really does
   capture Russian /voda/, Polish /voda/, etc.).

### Explicit non-goals

- No editing of candidates / re-running pipeline from UI (read-only).
- No authentication, no multi-user state.
- No hosted deployment; runs on `localhost` only.
- No graph layout editing / export beyond screenshots.
- Not responsive — desktop browser only.

## Architecture

```
┌─────────────────┐           ┌────────────────────┐
│  pangloss CLI   │  writes   │ output/            │
│  (existing)     ├──────────►│   dictionary.json  │
│                 │           │   graphs/*.json    │
└─────────────────┘           │   trace/*.json     │◄── NEW: selector trace dump
                              └──────────┬─────────┘
                                         │ reads
                              ┌──────────▼─────────┐
                              │  pangloss serve    │  NEW: FastAPI/Flask server
                              │  (new CLI verb)    │
                              │  localhost:8000    │
                              └──────────┬─────────┘
                                         │ serves
                              ┌──────────▼─────────┐
                              │  static SPA        │
                              │  (HTML+JS+D3)      │
                              └────────────────────┘
```

- **No new heavy frameworks**: plain HTML + vanilla JS + D3.js for the
  graph (CDN or vendored single file). No React/Vue/build tooling.
- **Server**: FastAPI (if already-allowed dep) or stdlib `http.server`
  — just serves the static SPA and JSON files from `output/`.
- **Data flow**: CLI runs normally, writes JSON artifacts. Server is a
  thin JSON-over-HTTP layer over those files. UI is pure client-side.

## Tasks

### W0 — Expand concept set from Swadesh-40 to Swadesh-100  `[ ]`

**Why**: User directive (2026-04-19): "Нам ещё нужны фонемы очевидно для
большего числа слов." 40 concepts is too few to:
- Diagnose systemic generator patterns (33/40 having 1 synonym could be
  a 100% dataset artifact; need more data to tell).
- Validate the canonical alphabet frequency table (rare graphemes like
  `ng`, `sh`, `f` have tiny sample sizes at n=40).
- Populate the homonym-guard registry meaningfully (P3 only bites when
  you have many concepts competing for the same short forms).
- Make frequency ranking (v3 T1) statistically meaningful.

**Data reality** (verified 2026-04-19):
- ASJP `parameters.csv` contains **exactly 100 concepts** (Swadesh-100).
- Current code hard-filters to 40 "starred" (`name.startswith('*')`)
  in `pangloss/data/asjp.py:102-104`.
- The other 60 are standard Swadesh entries without the `*` prefix:
  `this, that, who, what, not, all, many, big, long, small, woman, man,
  bird, seed, root, bark, flesh, grease, egg, tail, feather, hair, head,
  mouth, claw, foot, belly, neck, heart, eat, bite, know, sleep, kill,
  swim, fly, walk, lie, sit, stand, give, say, moon, rain, sand, earth,
  cloud, smoke, ash, burn, red, green, yellow, white, black, hot, cold,
  good, round, dry`.
- ASJP contains only Swadesh-100. `mouse` specifically is NOT in ASJP.
  Adding concepts beyond Swadesh-100 would require a different source
  (NorthEuraLex, CLICS, IDS) — out of scope for W0.

**Tasks**:
1. Change `_parse_core_concepts` in `pangloss/data/asjp.py` to include
   ALL 100 concepts (drop the `*` filter). Keep the `*` prefix in the
   returned names for backward compat OR normalize away the prefix
   entirely — **decide in implementation** based on downstream cost.
2. Update `ValueError` at line 107 from `!= 40` to `!= 100`.
3. **Invalidate matrix cache** (`data/matrix_cache.json`) on first
   run — different concept set means different cache hash. Verify the
   hash invalidation logic actually triggers.
4. Regenerate `docs/alphabet.md` frequency table from the new lexicon.
5. Update all hardcoded assumptions "40 concepts" in:
   - `README.md` (if it mentions 40)
   - `.sisyphus/notepads/`
   - CLI `--help` text if any number appears
6. Sanity check: run pipeline end-to-end, confirm no crashes on the
   new concepts (pronouns `this/that/who/what` and grammatical words
   `not/all/many` may have weirder ASJP forms than nouns).

**Acceptance**:
- `pangloss generate` produces a dictionary with 100 concepts (not 40).
- All 100 concepts complete processing without exceptions.
- Grapheme frequency table in `docs/alphabet.md` regenerated with
  n=100 data; note which graphemes changed rank significantly.
- Matrix cache regenerated; second run hits cache (performance
  unchanged).
- At least 5 of the new concepts (e.g., `mouth`, `head`, `moon`,
  `red`, `eat`) inspected manually — do their synonyms look sane?

**Risks**:
- Pronouns (`I`, `you`, `we`, `this`, `that`) often share phonemes
  across families (`m`/`n` nasals). May produce collision-prone
  synonyms. Acceptable for W0 — goal is just "more data to inspect",
  not quality. W6 will find problems, W7 plans fixes.
- Color terms (`red/green/yellow/white/black`) have cultural variance
  (Berlin-Kay). Generator doesn't care, it's all phonetics.
- Numeral `one` was already the worst-behaved concept in Swadesh-40;
  expect `two` (already there) and absence of higher numerals.

**Out of scope for W0**:
- Going beyond Swadesh-100 (requires new data sources).
- Improving any concept's output quality — W0 just lifts the ceiling on
  what's available for inspection.
- Translating concept names to Russian/other (they stay English).

### W1 — Extend pipeline to dump selector trace  `[ ]`
Modify `pangloss/algo/selector.py` to optionally emit a trace log:
- Per-step record: iteration, candidate chosen, speakers gained,
  languages gained, current coverage %, candidates rejected this round
  and why (already covered / below threshold / zero delta).
- Loop exit reason: threshold reached / no more candidates / no delta.
- Write to `output/trace/<concept>.json` when `--emit-trace` flag set.
- **Zero-overhead when flag off** (P2 rationale: debug instrumentation
  must not tax production runs).

### W2 — Static SPA shell  `[ ]`
Create `web/` directory:
- `web/index.html` — layout: left (graph), right-top (candidate table),
  right-bottom (trace log), top bar (concept selector + refresh).
- `web/app.js` — fetch `dictionary.json`, `graphs/<c>.json`,
  `trace/<c>.json`, render.
- `web/style.css` — minimal, readable, not fancy. Dark mode optional.
- No build step. `file://` opens must work (for offline).

### W3 — Bowtie graph component  `[ ]`
D3 force-directed or tree layout:
- Prefix trie on left (root expands rightward).
- Suffix trie on right (root expands leftward, mirrored).
- Convergence points as middle nodes joining a prefix path + suffix
  path.
- Node radius = log(speaker_count).
- Hover: show phoneme path, languages, speakers.
- Click: highlights this cluster's languages in the candidate table.

### W4 — Candidate & trace panels  `[ ]`
- Table: all `SyntheticWord`s for the concept. Sortable columns.
- Row color: green if selected, gray if rejected.
- "Why rejected?" tooltip using the trace.
- Trace panel: scrollable log, each step linked to the table row that
  was chosen at that step.

### W5 — `pangloss serve` CLI verb  `[ ]`
```bash
pangloss serve --output-dir output --port 8000
```
- Serves `web/` + `output/` as static files.
- Opens browser automatically (optional `--no-open`).
- Lists available concepts at `/` index page.

### W6 — Validate on the problematic concepts  `[ ]`
Use the new UI to document findings for:
- `*water` — why `wota` and `wotar` are kept separate (verify: coverage
  sets are actually disjoint).
- `*one` — why so many long hybrids? Hypothesis: numeral systems
  differ wildly across families so no small cluster dominates.
- `*eye`, `*tooth`, `*ear`, `*tongue` (all single-synonym) — what
  candidates were generated but rejected? Is the threshold too greedy?
- `*dog` — why 1 synonym at only 15.9% coverage? Are we missing
  germanic/slavic `hund`/`dog`/`pies` clusters?

Write findings to `.sisyphus/notepads/pangloss-v2.5/findings.md`. These
findings feed into the generation-finalization work that follows v2.5.

### W7 — Finalization decisions (depends on W6 findings)  `[ ]`
Based on what W6 reveals, produce a short doc-set decisions file for
what to fix in generation BEFORE v3 starts:
- Adjust selector threshold? Coverage floor per concept?
- Kill near-dupe heuristic? (e.g., if form A is form B with 1 extra
  trailing consonant AND coverage overlap > 50%, drop the longer one.)
- Cap hybrid length per concept? Minimum cluster size?
- Better handling of pronouns / numerals?

Output: `.sisyphus/plans/pangloss-v2.7-generation-finalization.md` with
concrete tasks to implement fixes BEFORE v3 resumes.

### W8 — README rewrite: decisions & motivation  `[ ]`
**User directive (2026-04-19)**: "Если делаем веб то надо в Ридми
описать решения, мотивацию." The current `README.md` is a stub that
describes WHAT the tool is. Once the web UI ships, the README must
also explain WHY the tool is the way it is.

Rewrite `README.md` to include these sections (in addition to the
existing install/quickstart):

1. **Motivation — Why Pangloss exists**
   - The problem: 7000+ languages, no shared vocabulary, Esperanto-
     style a-priori constructed languages ignore cross-family phonetic
     reality.
   - The bet: a synthetic word can be recognizable to speakers of many
     languages if it sits on a phonetic convergence point across
     families.

2. **Core Design Decisions (with rationale)**
   - Why ASJP as the phonetic source (not IPA dictionaries).
   - Why the reduced canonical alphabet (link to `docs/alphabet.md`).
   - Why 5 vowels, voicing collapse, labial merger.
   - Why greedy weighted set cover for selection (vs ILP / other).
   - Why convergence on bowtie (prefix+suffix) tries.
   - Why fuzzy phoneme matching via articulatory features.
   - Why hybrid merging of nearby clusters.
   - Why synonyms allowed within a concept, but homonyms banned across
     concepts (P3/P4 from Language Design Principles).

3. **How to read a Pangloss form** (link/inline from `docs/alphabet.md`
   "How to Read a Pangloss Form" section).

4. **The Web Inspector** — what it shows, when to use it, how to run
   `pangloss serve`. Include a screenshot.

5. **Known Limitations**
   - Swadesh-level vocabulary only (expanding in W0, but still bounded).
   - No morphology / phonotactics / prosody.
   - Coverage is per-concept and per-language, not per-speaker-
     recognition (we don't claim a Russian will DEFINITELY recognize
     `wota`, only that the phonetic cluster exists).
   - Canonical alphabet is many-to-one; forms are not IPA-reversible.

6. **Project Status & Roadmap** — link to `.sisyphus/plans/`, explain
   v2 (done), v2.5 (this milestone), v2.7, v3.

**Acceptance**:
- README renders correctly on GitHub (heading hierarchy, links, code
  blocks).
- Every major algorithmic decision has a 1-2 sentence "why" explanation
  accessible from the README (inline or linked to docs/notepads).
- A new contributor can read the README and understand the project's
  intent in < 10 minutes.
- No broken links. No references to files that don't exist.

## Success Criteria

- Can open `localhost:8000/?concept=water` and see the bowtie graph
  within 2 seconds on a warm CLI cache.
- Every synonym in the dictionary can be traced back to a specific
  convergence point and the languages it claims to cover, in the UI.
- Every rejected candidate has a visible reason for rejection.
- User completes W6 investigation without needing to inspect JSON by
  hand.
- No regression in CLI behavior when `--emit-trace` is not passed.
- **Concept count expanded from 40 → 100** (W0). Pipeline runs on the
  full Swadesh-100 without errors. Grapheme frequency table in
  `docs/alphabet.md` refreshed with n=100 data.
- README explains the project's WHY, not just HOW (W8).
- Handoff document (`pangloss-v2.7-generation-finalization.md`)
  exists and lists concrete fixes derived from UI-driven findings.

## Must NOT Have

- No new heavy frameworks (no React/Vue/Svelte/Next/build-tooling).
- No database, no auth, no accounts, no persistence beyond JSON files.
- No write operations from UI (read-only inspection).
- No network requests to external services (fully offline-capable).
- No regression of v2 bug fixes.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| D3 force layout slow for 500+ nodes | Use tree layout for the tries (deterministic, fast); force layout only for convergence cluster overlay. Prune nodes with < N speakers if perf drags. |
| `http.server` + static files won't let SPA fetch `output/` | Server always serves `output/` as `/output/*` path; SPA uses relative fetches. |
| Selector trace adds latency even when flag off | Conditional branch at top of loop; trace list stays empty; zero cost measured in W1 acceptance. |
| UI becomes a distraction from finalization | W6 is **mandatory** before v2.5 closes — UI is a means, not an end. No v2.5 "complete" without written findings. |
| ASJP source data genuinely bad for some concepts | UI will reveal this; W7 may conclude "nothing to fix, concept X is just hard" — that's a valid outcome, document it. |

## Open Questions

1. Server framework: FastAPI (nicer DX) vs stdlib `http.server` (zero dep)?
2. Graph layout: D3 tree (cleaner) vs force-directed (shows clusters)?
3. Do we need a "compare two concepts side-by-side" view, or is single-concept enough for v2.5?
4. Should trace include per-language speaker breakdown, or just
   aggregate speaker count per step?

## Ordering & Dependencies

```
W0 (expand concepts) ─┐
                      │
W1 (trace dump) ──────┤
                      ├─► W5 (serve) ──► W6 (findings) ──► W7 (finalization plan)
W2 (SPA shell) ───────┤                        │                  │
W3 (graph) ───────────┤                        │                  │
W4 (tables) ──────────┘                        └──► W8 (README rewrite)
```

- W0 (concept expansion) is independent, can run in parallel with W1-W4.
- W1 can go in parallel with W2-W4 (independent files).
- W5 needs all four of W1-W4 + W0 data to serve.
- W6 is gated on a working UI and expanded concept set (so findings
  are representative, not Swadesh-40-only artifacts).
- W7 is gated on W6.
- **W8 (README rewrite) is gated on W6** — only after we understand what
  Pangloss actually is can we document it truthfully. W8 may run in
  parallel with W7.

## Handoff to v3

v3 (this file, top section) **does not resume** until:
- W7 produces `pangloss-v2.7-generation-finalization.md`
- v2.7 tasks are implemented and verified
- Lexicon regenerated under v2.7 rules shows acceptable baseline
  (TBD criteria — likely: median synonyms per concept ≥ 3, total
  coverage per concept ≥ 40% for top-20 concepts, zero obvious
  near-dupe pairs in output).

Only then v3's T0 (frequency source selection) becomes meaningful.
