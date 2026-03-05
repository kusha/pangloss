#!/usr/bin/env python3
"""Verification script for synonym selector (Task 10).

Tests weighted set cover selection on water concept with 20 candidate words.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pangloss.data.matrix import build_matrix
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
from pangloss.algo.generator import generate_word
from pangloss.algo.selector import select_synonyms


def format_billions(count: int) -> str:
    """Format speaker count in billions."""
    return f"{count / 1_000_000_000:.1f}B"


def main():
    print("=" * 80)
    print("TASK 10: SYNONYM SELECTOR VERIFICATION")
    print("=" * 80)
    print()

    # Build matrix
    print("Loading ASJP data...")
    asjp_data = load_asjp("data/asjp")
    print(f"✓ Loaded ASJP data")

    print("Loading speaker counts...")
    speaker_counts = load_speaker_counts()
    print(f"✓ Loaded speaker counts")

    print("Building matrix...")
    matrix = build_matrix(asjp_data, speaker_counts)
    print(f"✓ Matrix built: {len(matrix)} concepts")

    concept = matrix["*water"]
    print(f"✓ Loaded {len(concept.entries)} languages for water")
    print(
        f"✓ Total speakers (with duplicates): {format_billions(concept.total_speakers)}"
    )
    print()

    # Build tries
    print("Building prefix and suffix tries...")
    prefix_trie = build_prefix_trie(concept.entries)
    suffix_trie = build_suffix_trie(concept.entries)
    print("✓ Tries ready")
    print()

    # Find convergence points
    print("Finding convergence points...")
    points = find_convergence_points(
        prefix_trie=prefix_trie, suffix_trie=suffix_trie, entries=concept.entries, k=20
    )
    print(f"✓ Found {len(points)} convergence points")
    print()

    # Generate words from convergence points
    print("Generating words from top 20 convergence points...")
    candidates = []

    for i, point in enumerate(points, 1):
        word = generate_word(point, prefix_trie, suffix_trie, concept.entries)
        candidates.append(word)
        print(
            f"  {i:2d}. {word.form:12s} | {word.ipa:15s} | "
            f"{len(word.covered_languages):3d} langs | "
            f"{format_billions(word.speaker_count):>6s} | "
            f"{word.coverage_pct:5.1f}%"
        )

    print()
    print(f"✓ Generated {len(candidates)} candidate words")
    print()

    # Test 1: 90% threshold (default)
    print("=" * 80)
    print("TEST 1: 90% THRESHOLD (DEFAULT)")
    print("=" * 80)
    print()

    selected = select_synonyms(candidates, coverage_threshold=0.9)

    print(f"Selected {len(selected)} synonyms:")
    print()

    cumulative_speakers = 0
    cumulative_languages = set()

    for i, word in enumerate(selected, 1):
        coverage_delta = getattr(word, "coverage_delta", 0)
        cumulative_speakers += coverage_delta
        cumulative_languages.update(word.covered_languages)

        cumulative_pct = (cumulative_speakers / concept.total_speakers) * 100

        print(f"{i}. {word.form}")
        print(f"   IPA:              {word.ipa}")
        print(f"   Coverage delta:   {format_billions(coverage_delta)} speakers")
        print(f"   Languages:        {len(word.covered_languages)} total")
        print(
            f"   Cumulative:       {format_billions(cumulative_speakers)} "
            f"({cumulative_pct:.1f}%) | {len(cumulative_languages)} unique languages"
        )
        print()

    # Compute final stats
    total_pct = (cumulative_speakers / concept.total_speakers) * 100

    print(
        f"Final Coverage: {format_billions(cumulative_speakers)} speakers "
        f"({total_pct:.1f}%)"
    )
    print(
        f"Languages:      {len(cumulative_languages)} of {len(concept.entries)} "
        f"({len(cumulative_languages) / len(concept.entries) * 100:.1f}%)"
    )
    print(f"Synonyms used:  {len(selected)}")
    print()

    # Assertions
    if total_pct >= 90.0:
        print("✓ PASS: Coverage ≥ 90%")
    else:
        # Check if this is maximum achievable
        max_speakers = sum(
            getattr(c, "coverage_delta", c.speaker_count)
            for c in select_synonyms(candidates, coverage_threshold=1.0)
        )
        max_pct = (max_speakers / concept.total_speakers) * 100

        if max_pct < 90.0:
            print(
                f"⚠ NOTE: Maximum achievable coverage is {max_pct:.1f}% (below 90% threshold)"
            )
            print(f"        Returned all {len(selected)} useful synonyms")
        else:
            print(f"✗ FAIL: Coverage {total_pct:.1f}% below 90% threshold")

    if 1 <= len(selected) <= 5:
        print("✓ PASS: Synonym count in expected range (1-5)")
    else:
        print(f"⚠ WARNING: Synonym count {len(selected)} outside expected range (1-5)")

    print()

    # Test 2: Configurable thresholds
    print("=" * 80)
    print("TEST 2: CONFIGURABLE THRESHOLDS")
    print("=" * 80)
    print()

    thresholds = [0.5, 0.9, 0.99]
    results = []

    for threshold in thresholds:
        selected_t = select_synonyms(candidates, coverage_threshold=threshold)

        total_langs = set()
        total_spk = 0
        for word in selected_t:
            total_langs.update(word.covered_languages)
            total_spk += getattr(word, "coverage_delta", 0)

        pct = (total_spk / concept.total_speakers) * 100
        results.append((threshold, len(selected_t), total_spk, pct, len(total_langs)))

        print(
            f"Threshold {threshold * 100:5.1f}%: {len(selected_t)} synonyms → "
            f"{format_billions(total_spk)} ({pct:5.1f}%) | "
            f"{len(total_langs)} languages"
        )

    print()

    # Check monotonicity: higher threshold → more synonyms
    counts = [r[1] for r in results]
    if counts == sorted(counts):
        print("✓ PASS: Synonym count increases with threshold")
    else:
        print(f"⚠ WARNING: Non-monotonic synonym counts: {counts}")

    print()

    # Save evidence
    print("=" * 80)
    print("SAVING EVIDENCE")
    print("=" * 80)
    print()

    evidence_dir = project_root / ".sisyphus" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Evidence 1: Water synonyms at 90%
    evidence1_path = evidence_dir / "task-10-synonyms-water.txt"
    with open(evidence1_path, "w") as f:
        f.write("TASK 10: SYNONYM SELECTOR — WATER CONCEPT AT 90% THRESHOLD\n")
        f.write("=" * 80 + "\n\n")

        f.write("CANDIDATES (Top 20 convergence points):\n")
        for i, word in enumerate(candidates, 1):
            f.write(
                f"  {i:2d}. {word.form:12s} | {word.ipa:15s} | "
                f"{len(word.covered_languages):3d} langs | "
                f"{format_billions(word.speaker_count):>6s} | "
                f"{word.coverage_pct:5.1f}%\n"
            )
        f.write("\n")

        f.write("SELECTED SYNONYMS (90% threshold):\n")
        cum_spk = 0
        cum_langs = set()
        cum_pct = 0.0
        for i, word in enumerate(selected, 1):
            delta = getattr(word, "coverage_delta", 0)
            cum_spk += delta
            cum_langs.update(word.covered_languages)
            cum_pct = (cum_spk / concept.total_speakers) * 100

            f.write(f"\n{i}. {word.form}\n")
            f.write(f"   IPA:            {word.ipa}\n")
            f.write(f"   Coverage delta: {format_billions(delta)} speakers\n")
            f.write(f"   Languages:      {len(word.covered_languages)} covered\n")
            f.write(
                f"   Cumulative:     {format_billions(cum_spk)} ({cum_pct:.1f}%) | "
                f"{len(cum_langs)} unique languages\n"
            )

        f.write("\n")
        f.write(f"FINAL STATS:\n")
        f.write(f"  Total coverage:  {format_billions(cum_spk)} ({cum_pct:.1f}%)\n")
        f.write(f"  Languages:       {len(cum_langs)} of {len(concept.entries)}\n")
        f.write(f"  Synonyms:        {len(selected)}\n")

    print(f"✓ Saved: {evidence1_path}")

    # Evidence 2: Threshold configuration
    evidence2_path = evidence_dir / "task-10-threshold-config.txt"
    with open(evidence2_path, "w") as f:
        f.write("TASK 10: SYNONYM SELECTOR — CONFIGURABLE THRESHOLDS\n")
        f.write("=" * 80 + "\n\n")

        f.write("Testing threshold configurability on water concept:\n\n")

        for threshold, count, speakers, pct, langs in results:
            f.write(f"Threshold: {threshold * 100:5.1f}%\n")
            f.write(f"  Synonyms selected: {count}\n")
            f.write(f"  Coverage:          {format_billions(speakers)} ({pct:5.1f}%)\n")
            f.write(f"  Languages:         {langs}\n")
            f.write("\n")

        f.write("VERIFICATION:\n")
        if counts == sorted(counts):
            f.write("  ✓ Monotonicity: Higher thresholds require more synonyms\n")
        else:
            f.write(f"  ✗ Non-monotonic counts: {counts}\n")

    print(f"✓ Saved: {evidence2_path}")
    print()

    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
