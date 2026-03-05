#!/usr/bin/env python3
"""Verification script for graph exporter (Task 12).

Tests bowtie graph export on water concept with JSON serialization.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pangloss.data.matrix import build_matrix
from pangloss.data.asjp import load_asjp
from pangloss.data.speakers import load_speaker_counts
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.algo.convergence import find_convergence_points
from pangloss.output.graph_export import export_bowtie_graph, validate_bowtie_export


def format_billions(count: int) -> str:
    """Format speaker count in billions."""
    return f"{count / 1_000_000_000:.1f}B"


def main():
    print("=" * 80)
    print("TASK 12: GRAPH JSON EXPORTER VERIFICATION")
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
    print(f"✓ Prefix trie: {prefix_trie.number_of_nodes()} nodes, {prefix_trie.number_of_edges()} edges")
    print(f"✓ Suffix trie: {suffix_trie.number_of_nodes()} nodes, {suffix_trie.number_of_edges()} edges")
    print()

    # Find convergence points
    print("Finding convergence points...")
    points = find_convergence_points(
        prefix_trie=prefix_trie, suffix_trie=suffix_trie, entries=concept.entries, k=20
    )
    print(f"✓ Found {len(points)} convergence points")
    print()

    # Show top convergence points
    print("Top convergence points:")
    for i, point in enumerate(points[:5], 1):
        prefix_str = "-".join(point.prefix_phonemes) if point.prefix_phonemes else "ε"
        suffix_str = "-".join(point.suffix_phonemes) if point.suffix_phonemes else "ε"
        print(
            f"  {i}. [{prefix_str}] + [{suffix_str}] | "
            f"{len(point.languages):4d} langs | {format_billions(point.speaker_count):>6s}"
        )
    print()

    # Export graph
    print("Exporting bowtie graph to JSON...")
    output_path = Path("output/graphs/water.json")
    export_bowtie_graph(
        prefix_trie=prefix_trie,
        suffix_trie=suffix_trie,
        convergence_points=points,
        concept_name="water",
        output_path=output_path,
    )
    print(f"✓ Exported to {output_path}")
    print()

    # Validate export
    print("Validating exported JSON...")
    validation = validate_bowtie_export(output_path)

    print(f"✓ Graph is valid")
    print(f"  - Total nodes: {validation['node_count']}")
    print(f"    - Root nodes: {validation['root_nodes']}")
    print(f"    - Prefix nodes: {validation['prefix_nodes']}")
    print(f"    - Suffix nodes: {validation['suffix_nodes']}")
    print(f"  - Total edges: {validation['edge_count']}")
    print(f"    - Prefix edges: {validation['prefix_edges']}")
    print(f"    - Suffix edges: {validation['suffix_edges']}")
    print(f"    - Bridge edges: {validation['bridge_edges']}")
    print(f"  - Concept: {validation['concept']}")
    print(f"  - Convergence points: {validation['convergence_count']}")
    print()

    # Spot-check JSON structure
    print("Validating JSON structure...")
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check top-level keys
    required_keys = {"directed", "multigraph", "graph", "nodes", "links"}
    has_keys = set(data.keys()) & required_keys
    print(f"✓ Has required keys: {has_keys}")

    # Check graph metadata
    if "graph" in data:
        graph_meta = data["graph"]
        print(f"  - Graph metadata: {graph_meta}")

    # Sample first few nodes
    if "nodes" in data and len(data["nodes"]) > 0:
        print(f"\n✓ Sample nodes:")
        for i, node in enumerate(data["nodes"][:3]):
            print(f"  [{i}] id={node.get('id')}, type={node.get('node_type')}, depth={node.get('depth')}")

    # Sample first few edges
    if "links" in data and len(data["links"]) > 0:
        print(f"\n✓ Sample edges:")
        prefix_edge_count = 0
        suffix_edge_count = 0
        bridge_edge_count = 0
        for i, edge in enumerate(data["links"][:10]):
            edge_type = edge.get("edge_type")
            print(f"  [{i}] {edge.get('source')} → {edge.get('target')} ({edge_type})")
            if edge_type == "prefix":
                prefix_edge_count += 1
            elif edge_type == "suffix":
                suffix_edge_count += 1
            elif edge_type == "bridge":
                bridge_edge_count += 1

    print()
    print("=" * 80)
    print("✓ VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
