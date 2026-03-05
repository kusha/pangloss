"""Prefix and Suffix trie builders for phoneme sequences.

This module implements phoneme-level prefix and suffix tries using NetworkX DiGraph.
- Prefix trie: Captures shared word beginnings (left→right insertion)
- Suffix trie: Captures shared word endings (right→left, reversed phoneme insertion)

Both tries reveal which phoneme patterns are shared by which language families,
weighted by speaker populations.

Key concepts:
- Root node at 'ε' (epsilon, empty string)
- Each edge represents adding one phoneme to the sequence
- Node attributes: phoneme_sequence, depth, languages (set), speaker_count
- Edge attributes: phoneme, languages (set), type="prefix"|"suffix"
- Suffix trie: phoneme_sequence is REVERSED (stores endings right→left)
"""

from typing import Any
import networkx as nx


def _insert_into_trie(
    trie: nx.DiGraph,
    phonemes: list[str],
    entry: Any,
    edge_type: str = "prefix",
) -> None:
    """Shared core logic for inserting phoneme sequences into tries.

    For suffix tries, pass reversed phonemes to this function.

    Args:
        trie: NetworkX DiGraph (modified in-place)
        phonemes: List of phonemes (reversed for suffix tries)
        entry: MatrixEntry with language_id, speaker_count
        edge_type: "prefix" or "suffix"
    """
    parent_id = "ε"

    for i, phoneme in enumerate(phonemes):
        phoneme_sequence = phonemes[: i + 1]
        node_id = "-".join(phoneme_sequence)

        if not trie.has_node(node_id):
            trie.add_node(
                node_id,
                phoneme_sequence=phoneme_sequence.copy(),
                depth=i + 1,
                languages=set(),
                speaker_count=0,
            )

        if not trie.has_edge(parent_id, node_id):
            trie.add_edge(
                parent_id, node_id, phoneme=phoneme, languages=set(), type=edge_type
            )

        trie.nodes[node_id]["languages"].add(entry.language_id)
        trie.nodes[node_id]["speaker_count"] += entry.speaker_count
        trie.edges[parent_id, node_id]["languages"].add(entry.language_id)

        parent_id = node_id


def build_prefix_trie(entries: list[Any]) -> nx.DiGraph:
    """Build prefix trie from phoneme sequences, left to right.

    Args:
        entries: List of MatrixEntry objects

    Returns:
        nx.DiGraph with root 'ε', node attrs (phoneme_sequence, depth, languages, speaker_count),
        edge attrs (phoneme, languages, type="prefix")
    """
    trie = nx.DiGraph()
    trie.add_node("ε", phoneme_sequence=[], depth=0, languages=set(), speaker_count=0)

    all_languages = set()

    for entry in entries:
        all_languages.add(entry.language_id)
        _insert_into_trie(trie, entry.phonemes, entry, edge_type="prefix")

    trie.graph["total_languages"] = len(all_languages)
    trie.graph["total_entries"] = len(entries)
    trie.graph["trie_type"] = "prefix"
    trie.graph["total_speaker_count"] = sum(entry.speaker_count for entry in entries)

    return trie


def build_suffix_trie(entries: list[Any]) -> nx.DiGraph:
    """Build suffix trie by reversing phoneme sequences before insertion.

    Args:
        entries: List of MatrixEntry objects

    Returns:
        nx.DiGraph with root 'ε', node attrs (phoneme_sequence, depth, languages, speaker_count),
        edge attrs (phoneme, languages, type="suffix"). Note: phoneme_sequence is REVERSED.
    """
    trie = nx.DiGraph()
    trie.add_node("ε", phoneme_sequence=[], depth=0, languages=set(), speaker_count=0)

    all_languages = set()

    for entry in entries:
        all_languages.add(entry.language_id)
        reversed_phonemes = list(reversed(entry.phonemes))
        _insert_into_trie(trie, reversed_phonemes, entry, edge_type="suffix")

    trie.graph["total_languages"] = len(all_languages)
    trie.graph["total_entries"] = len(entries)
    trie.graph["trie_type"] = "suffix"
    trie.graph["total_speaker_count"] = sum(entry.speaker_count for entry in entries)

    return trie


def get_node_score(trie: nx.DiGraph, node_id: str) -> float:
    """Calculate node score: depth × speaker_count."""
    node_attrs = trie.nodes[node_id]
    return node_attrs["depth"] * node_attrs["speaker_count"]
