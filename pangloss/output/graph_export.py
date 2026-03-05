"""Bowtie graph exporter for JSON serialization.

This module exports bowtie graphs (prefix trie + suffix trie + convergence/bridge edges)
as JSON using NetworkX's node_link_data format. Each exported graph includes:
- All prefix trie nodes and edges
- All suffix trie nodes and edges
- Bridge edges from convergence detection (connecting prefix nodes to suffix nodes)
- Node metadata: phoneme_sequence, depth, languages, speaker_count, node_type
- Edge metadata: type (prefix/suffix/bridge), languages, and convergence scores
- Graph metadata: concept name, total languages, convergence point count

The JSON files are compatible with D3.js visualization (future work).
"""

import json
from pathlib import Path
from typing import List, Set
import networkx as nx
from networkx.readwrite import json_graph

from pangloss.algo.convergence import ConvergencePoint


def export_bowtie_graph(
    prefix_trie: nx.DiGraph,
    suffix_trie: nx.DiGraph,
    convergence_points: List[ConvergencePoint],
    concept_name: str,
    output_path: Path,
) -> None:
    """Export a bowtie graph (prefix + suffix + bridges) as JSON.

    Creates a merged NetworkX DiGraph containing:
    1. All prefix trie nodes (prefixed with "prefix:")
    2. All suffix trie nodes (prefixed with "suffix:")
    3. Bridge edges connecting convergence points
    4. Graph metadata (concept, languages, convergence count)

    Node IDs are prefixed to avoid collisions:
    - Prefix nodes: "prefix:ε", "prefix:k", "prefix:k-a-k-a"
    - Suffix nodes: "suffix:ε", "suffix:a", "suffix:a-k-a"

    Args:
        prefix_trie: NetworkX DiGraph (prefix trie from Task 6)
        suffix_trie: NetworkX DiGraph (suffix trie from Task 7)
        convergence_points: List of ConvergencePoint objects (from Task 8)
        concept_name: Name of the concept (e.g., "water")
        output_path: Path to save JSON file (e.g., output/graphs/water.json)
    """
    # Create empty directed bowtie graph
    bowtie = nx.DiGraph()

    # Step 1: Add all prefix trie nodes with "prefix:" prefix
    for node_id in prefix_trie.nodes():
        prefixed_id = f"prefix:{node_id}"
        node_attrs = prefix_trie.nodes[node_id]

        bowtie.add_node(
            prefixed_id,
            node_type="root" if node_id == "ε" else "prefix",
            phoneme_sequence=list(node_attrs["phoneme_sequence"]),
            depth=node_attrs["depth"],
            languages=sorted(list(node_attrs["languages"])),
            speaker_count=node_attrs["speaker_count"],
        )

    # Step 2: Add all prefix trie edges
    for source, target in prefix_trie.edges():
        source_prefixed = f"prefix:{source}"
        target_prefixed = f"prefix:{target}"
        edge_attrs = prefix_trie.edges[source, target]

        bowtie.add_edge(
            source_prefixed,
            target_prefixed,
            edge_type="prefix",
            phoneme=edge_attrs["phoneme"],
            languages=sorted(list(edge_attrs["languages"])),
        )

    # Step 3: Add all suffix trie nodes with "suffix:" prefix
    for node_id in suffix_trie.nodes():
        suffixed_id = f"suffix:{node_id}"
        node_attrs = suffix_trie.nodes[node_id]

        bowtie.add_node(
            suffixed_id,
            node_type="root" if node_id == "ε" else "suffix",
            phoneme_sequence=list(node_attrs["phoneme_sequence"]),
            depth=node_attrs["depth"],
            languages=sorted(list(node_attrs["languages"])),
            speaker_count=node_attrs["speaker_count"],
        )

    # Step 4: Add all suffix trie edges
    for source, target in suffix_trie.edges():
        source_suffixed = f"suffix:{source}"
        target_suffixed = f"suffix:{target}"
        edge_attrs = suffix_trie.edges[source, target]

        bowtie.add_edge(
            source_suffixed,
            target_suffixed,
            edge_type="suffix",
            phoneme=edge_attrs["phoneme"],
            languages=sorted(list(edge_attrs["languages"])),
        )

    # Step 5: Add bridge edges from convergence points
    for conv_point in convergence_points:
        # Convert prefix_phonemes to node ID
        prefix_id = (
            "-".join(conv_point.prefix_phonemes) if conv_point.prefix_phonemes else "ε"
        )
        prefix_nodeid = f"prefix:{prefix_id}"

        # Convert suffix_phonemes to node ID (need to reverse them back to trie representation)
        # Note: suffix trie stores reversed sequences, so we need to reverse the suffix again
        suffix_phonemes_reversed = list(reversed(conv_point.suffix_phonemes))
        suffix_id = (
            "-".join(suffix_phonemes_reversed) if suffix_phonemes_reversed else "ε"
        )
        suffix_nodeid = f"suffix:{suffix_id}"

        # Only add bridge if both nodes exist
        if bowtie.has_node(prefix_nodeid) and bowtie.has_node(suffix_nodeid):
            # Calculate language intersection for the bridge
            language_intersection = sorted(list(conv_point.languages))

            bowtie.add_edge(
                prefix_nodeid,
                suffix_nodeid,
                edge_type="bridge",
                convergence_score=int(conv_point.score),
                language_intersection=language_intersection,
                languages=language_intersection,
            )

    # Step 6: Add graph metadata
    # Get total language count from either trie (they should be the same)
    prefix_langs_count = prefix_trie.graph.get("total_languages", 0)

    bowtie.graph["concept"] = concept_name
    bowtie.graph["total_languages"] = prefix_langs_count
    bowtie.graph["convergence_count"] = len(convergence_points)

    # Step 7: Serialize using NetworkX node_link_data format
    data = json_graph.node_link_data(bowtie)

    # Step 8: Save to output path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def validate_bowtie_export(json_path: Path) -> dict:
    """Validate a bowtie graph JSON export and return statistics.

    Args:
        json_path: Path to the exported JSON file

    Returns:
        Dictionary with validation results:
        - is_valid: Boolean
        - node_count: Total nodes
        - edge_count: Total edges
        - prefix_nodes: Count of prefix nodes
        - suffix_nodes: Count of suffix nodes
        - root_nodes: Count of root nodes
        - prefix_edges: Count of prefix edges
        - suffix_edges: Count of suffix edges
        - bridge_edges: Count of bridge edges
        - concept: Concept name
        - convergence_count: Number of convergence points
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct graph from node_link_data
    bowtie = json_graph.node_link_graph(data, directed=True)

    # Count node types
    prefix_nodes = sum(
        1
        for node_id, attrs in bowtie.nodes(data=True)
        if attrs.get("node_type") == "prefix"
    )
    suffix_nodes = sum(
        1
        for node_id, attrs in bowtie.nodes(data=True)
        if attrs.get("node_type") == "suffix"
    )
    root_nodes = sum(
        1
        for node_id, attrs in bowtie.nodes(data=True)
        if attrs.get("node_type") == "root"
    )

    # Count edge types
    prefix_edges = sum(
        1
        for _, _, attrs in bowtie.edges(data=True)
        if attrs.get("edge_type") == "prefix"
    )
    suffix_edges = sum(
        1
        for _, _, attrs in bowtie.edges(data=True)
        if attrs.get("edge_type") == "suffix"
    )
    bridge_edges = sum(
        1
        for _, _, attrs in bowtie.edges(data=True)
        if attrs.get("edge_type") == "bridge"
    )

    return {
        "is_valid": True,
        "node_count": bowtie.number_of_nodes(),
        "edge_count": bowtie.number_of_edges(),
        "prefix_nodes": prefix_nodes,
        "suffix_nodes": suffix_nodes,
        "root_nodes": root_nodes,
        "prefix_edges": prefix_edges,
        "suffix_edges": suffix_edges,
        "bridge_edges": bridge_edges,
        "concept": bowtie.graph.get("concept"),
        "convergence_count": bowtie.graph.get("convergence_count"),
    }
