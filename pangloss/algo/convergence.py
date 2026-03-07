"""
Phonetic Convergence Point Detector.

This module implements the core novel algorithm of Pangloss: identifying "convergence points"
in the phonetic space where many languages naturally cluster.

A convergence point is a pair of (prefix_node, suffix_node) in the phonetic tries that
maximizes the intersection of their language sets, weighted by speaker count. It reveals
phonetic universals (e.g., Romance languages clustering around /a/ or /ak/ for water).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import math
import networkx as nx

from pangloss.data.phonemes import (
    phoneme_distance,
    canonicalize_phoneme,
    canonicalize_sequence,
)


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
        is_hybrid: True if this point was synthesized from merging two clusters
    """

    prefix_phonemes: List[str]
    suffix_phonemes: List[str]
    languages: Set[str]
    speaker_count: int
    depth: int
    score: float
    is_hybrid: bool = False


def _is_fuzzy_phoneme_sequence_match(seq1: List[str], seq2: List[str]) -> bool:
    if len(seq1) != len(seq2):
        return False

    mismatch_count = 0
    for p1, p2 in zip(seq1, seq2):
        if p1 != p2:
            if phoneme_distance(p1, p2) >= 0.5:
                return False
            mismatch_count += 1
            if mismatch_count > 1:
                return False

    return mismatch_count == 1


def find_convergence_points(
    prefix_trie: nx.DiGraph,
    suffix_trie: nx.DiGraph,
    entries: List[Any],
    k: int = 10,
    distinctness_threshold: float = 0.5,
    fuzzy: bool = False,
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
        distinctness_threshold: Minimum score difference for deduplication
        fuzzy: If True, include near-matches (phoneme distance < 0.5) with 0.5x weight

    Returns:
        List of top-K ConvergencePoint objects, sorted by descending score.
    """
    # 1. Pre-compute language speaker counts for O(1) lookup during intersection scoring
    lang_speakers = {entry.language_id: entry.speaker_count for entry in entries}

    # 2. Pre-compute phoneme sequences by language for fuzzy matching
    lang_phonemes = (
        {entry.language_id: entry.phonemes for entry in entries} if fuzzy else {}
    )

    # 3. Collect all valid (prefix_id, suffix_id) split pairs from actual entries
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

        # Fuzzy matching: extend with near-matches if enabled
        fuzzy_langs = set()
        if fuzzy and intersect_langs:
            non_exact_langs = (p_langs | s_langs) - intersect_langs
            if non_exact_langs:
                for exact_lang_id in intersect_langs:
                    exact_phonemes = lang_phonemes.get(exact_lang_id)
                    if not exact_phonemes:
                        continue

                    for lang_id in non_exact_langs:
                        if lang_id in fuzzy_langs:
                            continue
                        lang_seq = lang_phonemes.get(lang_id)
                        if lang_seq and _is_fuzzy_phoneme_sequence_match(
                            lang_seq, exact_phonemes
                        ):
                            fuzzy_langs.add(lang_id)

        if not intersect_langs and not fuzzy_langs:
            continue

        # 4. Score the convergence point
        exact_speakers = sum(lang_speakers.get(lang, 0) for lang in intersect_langs)
        fuzzy_speakers = sum(lang_speakers.get(lang, 0) for lang in fuzzy_langs)
        speaker_count = exact_speakers + int(0.5 * fuzzy_speakers)

        # Depth indicates phonetic specificity (longer sequences = higher depth)
        p_depth = prefix_trie.nodes[prefix_id]["depth"]
        s_depth = suffix_trie.nodes[suffix_id]["depth"]
        depth = p_depth + s_depth

        # Skip epsilon-epsilon connections (depth 0) as they represent nothing
        if depth == 0:
            continue

        # Score formula: reward both specificity (depth) and coverage (speaker_count)
        score = float(depth * math.log1p(speaker_count))

        # Retrieve sequences for the dataclass (re-reverse suffix)
        p_seq = prefix_trie.nodes[prefix_id]["phoneme_sequence"]
        s_seq = list(reversed(suffix_trie.nodes[suffix_id]["phoneme_sequence"]))

        point = ConvergencePoint(
            prefix_phonemes=p_seq,
            suffix_phonemes=s_seq,
            languages=intersect_langs | fuzzy_langs,
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
            # Use Jaccard similarity for symmetric distinctness measure
            union_len = len(candidate.languages | selected.languages)
            if union_len > 0:
                jaccard = len(candidate.languages & selected.languages) / union_len
                if jaccard > distinctness_threshold:
                    is_distinct = False
                    break

        if is_distinct:
            distinct_points.append(candidate)
            if len(distinct_points) == k:
                break

    return distinct_points


def _are_mergeable(
    full_a: List[str],
    full_b: List[str],
    max_diffs: int = 2,
    max_phoneme_dist: float = 0.8,
) -> bool:
    """Check if two phoneme sequences are close enough to merge.

    Supports variable-length sequences: if they differ by exactly 1 trailing
    phoneme, the shorter is padded and that position counts as 1 diff.
    """
    len_diff = abs(len(full_a) - len(full_b))
    if len_diff > 1:
        return False
    if len(full_a) == 0 and len(full_b) == 0:
        return False

    # Pad shorter sequence so we can do positional comparison
    if len(full_a) < len(full_b):
        full_a = list(full_a) + [""]
    elif len(full_b) < len(full_a):
        full_b = list(full_b) + [""]

    canon_a = [canonicalize_phoneme(p) for p in full_a]
    canon_b = [canonicalize_phoneme(p) for p in full_b]

    diff_count = 0
    for c_a, c_b, p1, p2 in zip(canon_a, canon_b, full_a, full_b):
        if c_a == c_b:
            continue
        # Canonical forms differ — check articulatory distance on originals
        if p1 and p2:
            dist = phoneme_distance(p1, p2)
            if dist > max_phoneme_dist:
                return False
        diff_count += 1
        if diff_count > max_diffs:
            return False

    return diff_count >= 1


def _resolve_phoneme(
    p_a: str,
    p_b: str,
    speakers_a: int,
    speakers_b: int,
) -> str:
    """Deterministic phoneme resolution using canonical forms.

    Both phonemes are mapped to their canonical form. If they're the same
    canonical letter, return that directly. Otherwise, the canonical form
    of the higher-speaker phoneme wins; lexicographic tiebreak.
    """
    c_a = canonicalize_phoneme(p_a)
    c_b = canonicalize_phoneme(p_b)

    if c_a == c_b:
        return c_a if c_a else p_a

    if speakers_a > speakers_b:
        return c_a if c_a else c_b
    if speakers_b > speakers_a:
        return c_b if c_b else c_a
    return min(c_a, c_b) if (c_a and c_b) else (c_a or c_b)


def _compute_deduped_speakers(
    languages: Set[str],
    lang_speakers: Dict[str, int],
    asjp_to_iso: Dict[str, str],
) -> int:
    """Compute ISO-deduplicated speaker count for a set of ASJP language IDs.

    Multiple ASJP entries may share the same ISO 639-3 code (e.g., MANDARIN,
    MANDARIN_2, CHINESE_MANDARIN all map to 'zho'). Naively summing their
    speaker counts inflates the total. This function counts each ISO code
    only once, using the max speaker count among its ASJP variants.
    """
    iso_seen: Dict[str, int] = {}
    for lang in languages:
        iso = asjp_to_iso.get(lang)
        key = iso if iso else lang
        spk = lang_speakers.get(lang, 0)
        if key not in iso_seen or spk > iso_seen[key]:
            iso_seen[key] = spk
    return sum(iso_seen.values())


def merge_convergence_points(
    points: List[ConvergencePoint],
    lang_speakers: Dict[str, int],
    asjp_to_iso: Optional[Dict[str, str]] = None,
    max_diffs: int = 2,
    max_phoneme_dist: float = 0.8,
    min_jaccard_separation: float = 0.7,
) -> List[ConvergencePoint]:
    """Merge nearby convergence points into deterministic hybrid forms.

    For each pair of points with similar phoneme sequences but distinct
    language sets, synthesize a hybrid whose phonemes are resolved
    position-by-position by speaker-weighted voting.

    The hybrid replaces both originals if it covers more total speakers
    than either individual point.

    Args:
        points: Convergence points from find_convergence_points()
        lang_speakers: language_id → speaker_count mapping
        max_diffs: Max phoneme positions that may differ (default 2)
        max_phoneme_dist: Max articulatory distance at each differing position
        min_jaccard_separation: Min Jaccard distance (1 - Jaccard similarity)
            between language sets to consider merging. High value = clusters
            must be mostly disjoint. Default 0.7 means ≤30% overlap.

    Returns:
        List of ConvergencePoints — originals plus any hybrids that improve coverage.
        Sorted by score descending.
    """
    if len(points) <= 1:
        return list(points)

    merged_indices: Set[int] = set()
    hybrids: List[ConvergencePoint] = []

    for i in range(len(points)):
        if i in merged_indices:
            continue
        for j in range(i + 1, len(points)):
            if j in merged_indices:
                continue

            pt_a = points[i]
            pt_b = points[j]

            full_a = pt_a.prefix_phonemes + pt_a.suffix_phonemes
            full_b = pt_b.prefix_phonemes + pt_b.suffix_phonemes

            if not _are_mergeable(full_a, full_b, max_diffs, max_phoneme_dist):
                continue

            union_size = len(pt_a.languages | pt_b.languages)
            if union_size == 0:
                continue
            jaccard_sim = len(pt_a.languages & pt_b.languages) / union_size
            if (1.0 - jaccard_sim) < min_jaccard_separation:
                continue

            # Pad shorter sequence so zip covers the trailing phoneme
            padded_a = list(full_a)
            padded_b = list(full_b)
            if len(padded_a) < len(padded_b):
                padded_a.append("")
            elif len(padded_b) < len(padded_a):
                padded_b.append("")

            hybrid_phonemes: List[str] = []
            for p_a, p_b in zip(padded_a, padded_b):
                resolved = _resolve_phoneme(
                    p_a, p_b, pt_a.speaker_count, pt_b.speaker_count
                )
                if resolved:  # drop empty (e.g. glottal stop, padding)
                    hybrid_phonemes.append(resolved)

            # Split at pt_a's prefix length (higher-scoring, since list is score-sorted)
            split_at = min(len(pt_a.prefix_phonemes), len(hybrid_phonemes))
            hybrid_prefix = hybrid_phonemes[:split_at]
            hybrid_suffix = hybrid_phonemes[split_at:]

            hybrid_langs = pt_a.languages | pt_b.languages
            if asjp_to_iso:
                hybrid_speakers = _compute_deduped_speakers(
                    hybrid_langs, lang_speakers, asjp_to_iso
                )
            else:
                hybrid_speakers = sum(
                    lang_speakers.get(lang, 0) for lang in hybrid_langs
                )

            hybrid_depth = len(hybrid_phonemes)
            hybrid_score = float(hybrid_depth * math.log1p(hybrid_speakers))

            if asjp_to_iso:
                speakers_a = _compute_deduped_speakers(
                    pt_a.languages, lang_speakers, asjp_to_iso
                )
                speakers_b = _compute_deduped_speakers(
                    pt_b.languages, lang_speakers, asjp_to_iso
                )
            else:
                speakers_a = pt_a.speaker_count
                speakers_b = pt_b.speaker_count

            if hybrid_speakers <= speakers_a and hybrid_speakers <= speakers_b:
                continue

            hybrid = ConvergencePoint(
                prefix_phonemes=hybrid_prefix,
                suffix_phonemes=hybrid_suffix,
                languages=hybrid_langs,
                speaker_count=hybrid_speakers,
                depth=hybrid_depth,
                score=hybrid_score,
                is_hybrid=True,
            )

            hybrids.append(hybrid)
            merged_indices.add(i)
            merged_indices.add(j)
            break

    result = [pt for idx, pt in enumerate(points) if idx not in merged_indices]
    result.extend(hybrids)

    result.sort(key=lambda x: x.score, reverse=True)
    return result
