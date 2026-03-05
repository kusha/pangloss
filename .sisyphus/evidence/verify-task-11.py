#!/usr/bin/env python3
"""
Verification script for Task 11: Dictionary Output Formatter.

Runs full pipeline for water concept and validates dictionary structure.
"""

import sys
from pathlib import Path

# Add pangloss to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.data.matrix import build_matrix
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
from pangloss.algo.generator import generate_word
from pangloss.algo.selector import select_synonyms
from pangloss.output.dictionary import (
    format_dictionary,
    save_dictionary,
    format_summary,
)


def main():
    print("=== Task 11: Dictionary Output Formatter Verification ===\n")

    # Step 1: Load data
    print("[1/8] Loading ASJP dataset...")
    concepts = load_asjp(data_dir="data/asjp")
    water_concept = concepts["2"]  # Water is concept ID "2"
    print(f"  ✓ Water forms: {len(water_concept.forms)}")

    print("\n[2/8] Loading speaker counts...")
    speakers = load_speaker_counts()
    print(f"  ✓ Speaker data loaded: {len(speakers)} languages")

    # Step 2: Build matrix for water (only process water concept)
    print("\n[3/8] Building matrix for water concept...")
    water_only = {"2": concepts["2"]}
    concept_matrices = build_matrix(water_only, speakers)
    water_matrix = list(concept_matrices.values())[0]
    print(f"  ✓ Matrix entries: {len(water_matrix.entries)}")
    print(f"  ✓ Total speakers: {water_matrix.total_speakers:,}")

    # Step 3: Build tries
    print("\n[4/8] Building prefix trie...")
    prefix_trie = build_prefix_trie(water_matrix.entries)
    print(
        f"  ✓ Nodes: {prefix_trie.number_of_nodes()}, Edges: {prefix_trie.number_of_edges()}"
    )

    print("\n[5/8] Building suffix trie...")
    suffix_trie = build_suffix_trie(water_matrix.entries)
    print(
        f"  ✓ Nodes: {suffix_trie.number_of_nodes()}, Edges: {suffix_trie.number_of_edges()}"
    )

    # Step 4: Find convergence points
    print("\n[6/8] Finding convergence points...")
    convergence_points = find_convergence_points(
        prefix_trie=prefix_trie,
        suffix_trie=suffix_trie,
        entries=water_matrix.entries,
        k=20,
    )
    print(f"  ✓ Convergence points found: {len(convergence_points)}")

    # Step 5: Generate synthetic words
    print("\n[7/8] Generating synthetic words...")
    synthetic_words = []
    for cp in convergence_points:
        word = generate_word(
            convergence_point=cp,
            prefix_trie=prefix_trie,
            suffix_trie=suffix_trie,
            entries=water_matrix.entries,
        )
        synthetic_words.append(word)

    print(f"  ✓ Generated {len(synthetic_words)} candidate words")
    print(f"  ✓ Example word: {synthetic_words[0].form} ({synthetic_words[0].ipa})")

    # Step 6: Select synonyms
    print("\n[8/8] Selecting synonyms (90% coverage threshold)...")
    selected_synonyms = select_synonyms(synthetic_words, coverage_threshold=0.9)
    print(f"  ✓ Selected synonyms: {len(selected_synonyms)}")
    print(
        f"  ✓ Top synonym: {selected_synonyms[0].form} - {selected_synonyms[0].speaker_count:,} speakers"
    )

    # Step 7: Format dictionary
    print("\n[DICT] Formatting dictionary...")
    results = {"water": selected_synonyms}
    matrix_lookup = {"water": water_matrix.entries}
    dictionary = format_dictionary(results, matrix_entries=matrix_lookup)

    # Validate structure
    assert "concepts" in dictionary, "Missing 'concepts' key"
    assert len(dictionary["concepts"]) == 1, "Expected 1 concept"

    water_concept_dict = dictionary["concepts"][0]
    assert water_concept_dict["concept"] == "water", "Incorrect concept name"
    assert "synonyms" in water_concept_dict, "Missing 'synonyms' key"
    assert "total_coverage" in water_concept_dict, "Missing 'total_coverage' key"
    assert "total_speakers" in water_concept_dict, "Missing 'total_speakers' key"
    assert "language_families_covered" in water_concept_dict, (
        "Missing 'language_families_covered' key"
    )
    assert "synonym_count" in water_concept_dict, "Missing 'synonym_count' key"

    print(f"  ✓ Dictionary structure valid")
    print(f"  ✓ Concept: {water_concept_dict['concept']}")
    print(f"  ✓ Synonyms: {water_concept_dict['synonym_count']}")
    print(f"  ✓ Total coverage: {water_concept_dict['total_coverage']}%")
    print(f"  ✓ Total speakers: {water_concept_dict['total_speakers']:,}")
    print(
        f"  ✓ Language families: {len(water_concept_dict['language_families_covered'])}"
    )

    # Validate synonym structure
    first_synonym = water_concept_dict["synonyms"][0]
    assert "form" in first_synonym, "Missing 'form' in synonym"
    assert "ipa" in first_synonym, "Missing 'ipa' in synonym"
    assert "covers" in first_synonym, "Missing 'covers' in synonym"
    assert "speaker_count" in first_synonym, "Missing 'speaker_count' in synonym"
    assert "coverage_pct" in first_synonym, "Missing 'coverage_pct' in synonym"
    assert "source_pattern" in first_synonym, "Missing 'source_pattern' in synonym"
    assert "reasoning" in first_synonym, "Missing 'reasoning' in synonym"

    print(f"\n  ✓ Synonym structure valid")
    print(f"    Form: {first_synonym['form']}")
    print(f"    IPA: {first_synonym['ipa']}")
    print(f"    Covers: {len(first_synonym['covers'])} languages")
    print(f"    Speaker count: {first_synonym['speaker_count']:,}")
    print(f"    Coverage: {first_synonym['coverage_pct']}%")
    print(f"    Source pattern: {first_synonym['source_pattern']}")

    # Step 8: Generate summary
    print("\n[SUMMARY] Generating summary statistics...")
    summary = format_summary(dictionary)

    assert summary["total_concepts"] == 1, "Expected 1 concept in summary"
    assert summary["avg_coverage_pct"] > 0, "Expected positive average coverage"
    assert summary["total_unique_languages"] > 0, "Expected positive language count"

    print(f"  ✓ Total concepts: {summary['total_concepts']}")
    print(f"  ✓ Avg coverage: {summary['avg_coverage_pct']}%")
    print(f"  ✓ Min coverage: {summary['min_coverage_pct']}%")
    print(f"  ✓ Max coverage: {summary['max_coverage_pct']}%")
    print(f"  ✓ Avg synonym count: {summary['avg_synonym_count']}")
    print(f"  ✓ Total unique languages: {summary['total_unique_languages']}")
    print(f"  ✓ Total unique families: {summary['total_unique_families']}")

    # Step 9: Save dictionary to evidence files
    print("\n[SAVE] Saving evidence files...")
    evidence_dir = Path(__file__).parent

    dict_path = evidence_dir / "task-11-water-dict.json"
    save_dictionary(dictionary, str(dict_path), format="json")
    print(f"  ✓ Dictionary saved: {dict_path}")

    summary_path = evidence_dir / "task-11-summary-stats.json"
    import json

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Summary saved: {summary_path}")

    # Step 10: Create validation summary text
    validation_path = evidence_dir / "task-11-dictionary-valid.txt"
    with open(validation_path, "w", encoding="utf-8") as f:
        f.write("=== Task 11: Dictionary Output Formatter - Validation Summary ===\n\n")
        f.write(f"Dictionary Structure:\n")
        f.write(f"  - Concepts: {len(dictionary['concepts'])}\n")
        f.write(f"  - Synonyms for 'water': {water_concept_dict['synonym_count']}\n")
        f.write(f"  - Total coverage: {water_concept_dict['total_coverage']}%\n")
        f.write(f"  - Total speakers: {water_concept_dict['total_speakers']:,}\n")
        f.write(
            f"  - Language families covered: {len(water_concept_dict['language_families_covered'])}\n\n"
        )

        f.write(f"Top 3 Synonyms:\n")
        for i, syn in enumerate(water_concept_dict["synonyms"][:3], 1):
            f.write(f"  {i}. {syn['form']} ({syn['ipa']})\n")
            f.write(f"     - Covers: {len(syn['covers'])} languages\n")
            f.write(f"     - Speakers: {syn['speaker_count']:,}\n")
            f.write(f"     - Coverage: {syn['coverage_pct']}%\n")
            f.write(f"     - Pattern: {syn['source_pattern']}\n\n")

        f.write(f"Summary Statistics:\n")
        f.write(f"  - Total concepts: {summary['total_concepts']}\n")
        f.write(f"  - Avg coverage: {summary['avg_coverage_pct']}%\n")
        f.write(f"  - Unique languages: {summary['total_unique_languages']}\n")
        f.write(f"  - Unique families: {summary['total_unique_families']}\n\n")

        f.write("✓ All validations passed\n")

    print(f"  ✓ Validation summary saved: {validation_path}")

    print("\n=== SUCCESS: Dictionary formatter validated ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
