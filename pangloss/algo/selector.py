"""Synonym Selector — Weighted Set Cover

Greedy weighted set cover algorithm to select minimum synonyms achieving target coverage threshold.
"""

from typing import List, Set, Dict, Optional
from dataclasses import replace
from pangloss.algo.generator import SyntheticWord


def select_synonyms(
    candidates: List[SyntheticWord],
    coverage_threshold: float = 0.9,
    language_to_speakers: Optional[Dict[str, int]] = None,
    total_speakers: int = 0,
) -> List[SyntheticWord]:
    """Select minimum set of synonyms achieving target coverage threshold.

    Uses greedy weighted set cover: iteratively selects the candidate covering
    the most UNCOVERED speakers until the threshold is reached or no candidates
    add additional coverage.

    Args:
        candidates: List of SyntheticWord candidates to select from
        coverage_threshold: Target coverage as fraction (0.0 to 1.0), default 0.9 (90%)
        language_to_speakers: Maps language_id → speaker_count for exact marginal gains
        total_speakers: Total unique speakers for this concept (for coverage calculation)

    Returns:
        List of selected SyntheticWords, ordered by coverage contribution (descending).
        Each word has coverage_delta added to track speakers it contributed.

    Notes:
        - If max achievable coverage < threshold, returns all useful synonyms
        - Empty candidates list returns empty list
        - Coverage_delta is stored as an additional attribute on returned SyntheticWord objects
    """
    if not candidates:
        return []

    # Calculate total speakers across ALL candidates (max achievable)
    all_languages: Set[str] = set()
    for candidate in candidates:
        all_languages.update(candidate.covered_languages)

    # Get total speaker count from first candidate (they should all have same denominator)
    # We'll recalculate total from matrix data
    # For now, use sum of all unique language contributions
    # Actually, we need to track speaker count per language properly
    # The candidate.speaker_count is already the sum, but it may have duplicates

    # Build mapping of language -> speaker count from candidates
    # We'll use the fact that each candidate has covered_languages and we need to sum uniquely
    # Better approach: track uncovered as set of languages, compute speakers from first candidate's context

    # Since we don't have per-language speaker counts in SyntheticWord,
    # we'll use a simpler approach: track uncovered languages, compute coverage by language count ratio
    # But the task asks for speaker-based coverage, so we need to be careful

    # Re-reading the SyntheticWord structure:
    # - speaker_count: total speakers covered by THIS word
    # - covered_languages: Set[str] of language IDs
    # - coverage_pct: percentage coverage

    # The speaker_count has duplicates (Mandarin variants share counts)
    # For greedy selection, we need to track UNIQUE speakers per language

    # Since we don't have per-language breakdown, we'll approximate:
    # Use language set coverage as proxy, but report speaker_count for each selection

    # Better: Since each candidate has speaker_count and covered_languages,
    # we can infer average speakers per language for that cluster
    # Then estimate contribution based on uncovered languages

    # Simplest correct approach:
    # - Track uncovered_languages as Set[str]
    # - For each candidate, find intersection with uncovered_languages
    # - Estimate speakers added by proportion of languages added
    # - Select candidate with highest speaker contribution from uncovered set

    # Actually, let's use a more direct approach:
    # Each candidate already has speaker_count for its covered_languages
    # We can't easily decompose this without per-language data
    # Instead, we'll use LANGUAGE COUNT as the primary metric (unweighted set cover)
    # and report speaker_count as informational

    # Wait - the task says "weighted set cover" and "covering most UNCOVERED speakers"
    # This implies we need speaker-weighted selection

    # Let me reconsider: The speaker_count in SyntheticWord is inflated due to duplicates
    # The coverage_pct is calculated against total_speakers in the concept
    # We need the total_speakers value to compute proper percentages

    # Since candidates all come from the same concept, they share the same denominator
    # We can infer total from coverage_pct: total = speaker_count / (coverage_pct / 100)

    # Use total_speakers parameter directly (passed from caller)
    # If not provided, infer from first candidate's coverage_pct
    if total_speakers == 0 and candidates and candidates[0].coverage_pct > 0:
        total_speakers = int(
            candidates[0].speaker_count / (candidates[0].coverage_pct / 100.0)
        )
    elif total_speakers == 0:
        # Fallback: sum all speakers (may overcount due to overlaps)
        total_speakers = sum(c.speaker_count for c in candidates)

    # Track selected synonyms and covered languages
    selected: List[SyntheticWord] = []
    uncovered_languages: Set[str] = set(all_languages)
    covered_speakers = 0

    # Create working list of candidates
    remaining_candidates = list(candidates)

    while remaining_candidates and uncovered_languages:
        # Check if we've reached threshold
        current_coverage = (
            covered_speakers / total_speakers if total_speakers > 0 else 0.0
        )
        if current_coverage >= coverage_threshold:
            break

        # Find candidate covering most uncovered speakers
        best_candidate = None
        best_new_languages: Set[str] = set()
        best_estimated_speakers = 0

        for candidate in remaining_candidates:
            # Compute new coverage
            new_languages = candidate.covered_languages & uncovered_languages
            if not new_languages:
                continue

            # Use exact speaker counts per language when available
            if language_to_speakers:
                estimated_speakers = sum(
                    language_to_speakers.get(lang, 0) for lang in new_languages
                )
            else:
                # Fallback to proportional estimate
                if candidate.covered_languages:
                    language_ratio = len(new_languages) / len(
                        candidate.covered_languages
                    )
                    estimated_speakers = int(candidate.speaker_count * language_ratio)
                else:
                    estimated_speakers = 0

            # Select candidate with highest estimated speaker contribution
            if estimated_speakers > best_estimated_speakers:
                best_candidate = candidate
                best_new_languages = new_languages
                best_estimated_speakers = estimated_speakers

        # If no candidate adds coverage, stop
        if best_candidate is None:
            break

        # Add best candidate to selection
        selected_word = replace(best_candidate)
        object.__setattr__(selected_word, "coverage_delta", best_estimated_speakers)

        selected.append(selected_word)
        uncovered_languages -= best_new_languages
        covered_speakers += best_estimated_speakers
        remaining_candidates.remove(best_candidate)

    return selected
