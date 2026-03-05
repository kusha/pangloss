"""
Phonetic Convergence Point Detector.

This module implements the core novel algorithm of Pangloss: identifying "convergence points"
in the phonetic space where many languages naturally cluster.

A convergence point is a pair of (prefix_node, suffix_node) in the phonetic tries that
maximizes the intersection of their language sets, weighted by speaker count. It reveals
phonetic universals (e.g., Romance languages clustering around /a/ or /ak/ for water).
"""

from dataclasses import dataclass
from typing import Any, List, Set
import networkx as nx


@dataclass
class ConvergencePoint:
    """
    Represents a point of phonetic convergence across multiple languages.

    Attributes:
        prefix_phonemes: Shared prefix sequence (e.g., ['a', 'k'])
        suffix_phonemes: Shared suffix sequence (e.g., ['a'])
        languages: Set of language IDs sharing BOTH prefix and suffix
        speaker_count: Total speakers of those languages
        depth: Combined prefix + suffix depth (indicator of sequence length)
        score: Relevance score (typically depth * speaker_count)
    """

    prefix_phonemes: List[str]
    suffix_phonemes: List[str]
    languages: Set[str]
    speaker_count: int
    depth: int
    score: float


def find_convergence_points(
    prefix_trie: nx.DiGraph,
    suffix_trie: nx.DiGraph,
    entries: List[Any],
    k: int = 10,
) -> List[ConvergencePoint]:
    """
    Find the top-K phonetic convergence points for a concept.

    Algorithm:
    1. For each language's phoneme sequence, consider all possible split points.
    2. At each split, look up the corresponding prefix node and suffix node.
    3. Calculate the intersection of languages that pass through BOTH nodes.
    4. Weight the intersection by speaker count and combined depth.
    5. Return the top-K highest scoring convergence points.

    Args:
        prefix_trie: Built prefix trie (left→right)
        suffix_trie: Built suffix trie (right→left)
        entries: List of MatrixEntry objects for the concept
        k: Number of convergence points to return

    Returns:
        List of top-K ConvergencePoint objects, sorted by descending score.
    """
    # 1. Pre-compute language speaker counts for O(1) lookup during intersection scoring
    lang_speakers = {entry.language_id: entry.speaker_count for entry in entries}

    # 2. Collect all valid (prefix_id, suffix_id) split pairs from actual entries
    # We only consider pairs that naturally occur in at least one language's word
    split_pairs = set()
    for entry in entries:
        phonemes = entry.phonemes
        for i in range(len(phonemes) + 1):
            prefix_seq = phonemes[:i]
            suffix_seq = phonemes[i:]

            prefix_id = "-".join(prefix_seq) if prefix_seq else "ε"
            suffix_id = "-".join(reversed(suffix_seq)) if suffix_seq else "ε"

            split_pairs.add((prefix_id, suffix_id))

    # 3. Analyze each split pair to find language intersections
    convergence_points = []

    for prefix_id, suffix_id in split_pairs:
        # Safety check: nodes must exist in their respective tries
        if not prefix_trie.has_node(prefix_id) or not suffix_trie.has_node(suffix_id):
            continue

        p_langs = prefix_trie.nodes[prefix_id]["languages"]
        s_langs = suffix_trie.nodes[suffix_id]["languages"]

        # The core insight: which languages share THIS specific prefix AND suffix?
        intersect_langs = p_langs & s_langs

        if not intersect_langs:
            continue

        # 4. Score the convergence point
        speaker_count = sum(lang_speakers.get(lang, 0) for lang in intersect_langs)

        # Depth indicates phonetic specificity (longer sequences = higher depth)
        p_depth = prefix_trie.nodes[prefix_id]["depth"]
        s_depth = suffix_trie.nodes[suffix_id]["depth"]
        depth = p_depth + s_depth

        # Skip epsilon-epsilon connections (depth 0) as they represent nothing
        if depth == 0:
            continue

        # Score formula: reward both specificity (depth) and coverage (speaker_count)
        score = float(depth * speaker_count)

        # Retrieve sequences for the dataclass (re-reverse suffix)
        p_seq = prefix_trie.nodes[prefix_id]["phoneme_sequence"]
        s_seq = list(reversed(suffix_trie.nodes[suffix_id]["phoneme_sequence"]))

        point = ConvergencePoint(
            prefix_phonemes=p_seq,
            suffix_phonemes=s_seq,
            languages=intersect_langs,
            speaker_count=speaker_count,
            depth=depth,
            score=score,
        )
        convergence_points.append(point)

    # 5. Sort by score and select top-K distinct points
    convergence_points.sort(key=lambda x: x.score, reverse=True)

    distinct_points = []
    for candidate in convergence_points:
        if not distinct_points:
            distinct_points.append(candidate)
            continue

        # Ensure candidate represents a distinct phonetic cluster
        is_distinct = True
        for selected in distinct_points:
            overlap = len(candidate.languages & selected.languages)
            min_len = min(len(candidate.languages), len(selected.languages))

            # If >20% overlap, they cover the same language family
            if min_len > 0 and (overlap / min_len) > 0.2:
                is_distinct = False
                break

        if is_distinct:
            distinct_points.append(candidate)
            if len(distinct_points) == k:
                break

    return distinct_points
