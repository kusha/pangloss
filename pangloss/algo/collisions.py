"""Collision Detection — Exact, Near, and Within-Concept

Detects exact, near, and within-concept collisions for synthetic words across concepts.
"""

from typing import Dict, List, Tuple, Set
from difflib import SequenceMatcher
from pangloss.algo.generator import SyntheticWord


def detect_collisions(results: Dict[str, List[SyntheticWord]]) -> dict:
    """Detect collisions across all synthetic word concepts.

    Args:
        results: Dict mapping concept_name → list of SyntheticWord objects

    Returns:
        Dictionary with three collision categories:
        - exact_collisions: List of exact form/IPA matches across different concepts
        - near_collisions: List of near-matches (IPA similarity ≥ 0.85) across different concepts
        - within_concept_collisions: List of collisions within the same concept
    """
    exact_collisions = []
    near_collisions = []
    within_concept_collisions = []

    # === EXACT COLLISIONS ===
    # Build maps: normalized_form/IPA → list of (concept_name, SyntheticWord)
    form_map: Dict[str, List[Tuple[str, SyntheticWord]]] = {}
    ipa_map: Dict[str, List[Tuple[str, SyntheticWord]]] = {}

    for concept_name, words in results.items():
        for word in words:
            # Normalize form
            normalized_form = word.form.lower().strip()
            if normalized_form not in form_map:
                form_map[normalized_form] = []
            form_map[normalized_form].append((concept_name, word))

            # Normalize IPA
            normalized_ipa = word.ipa.lower().strip()
            if normalized_ipa not in ipa_map:
                ipa_map[normalized_ipa] = []
            ipa_map[normalized_ipa].append((concept_name, word))

    # Check for cross-concept collisions in form
    for normalized_form, entries in form_map.items():
        if len(entries) > 1:
            # Check if from different concepts
            concepts = {concept for concept, _ in entries}
            if len(concepts) > 1:
                exact_collisions.append(
                    {
                        "form": normalized_form,
                        "concepts": sorted(list(concepts)),
                        "type": "transliteration",
                    }
                )

    # Check for cross-concept collisions in IPA
    for normalized_ipa, entries in ipa_map.items():
        if len(entries) > 1:
            # Check if from different concepts
            concepts = {concept for concept, _ in entries}
            if len(concepts) > 1:
                exact_collisions.append(
                    {
                        "form": normalized_ipa,
                        "concepts": sorted(list(concepts)),
                        "type": "ipa",
                    }
                )

    # === NEAR-COLLISIONS ===
    # Collect all (concept, word) pairs
    all_pairs: List[Tuple[str, SyntheticWord]] = []
    for concept_name, words in results.items():
        for word in words:
            all_pairs.append((concept_name, word))

    # Check all pairs from different concepts
    seen_pairs: Set[Tuple[str, str, str, str]] = (
        set()
    )  # (c1, f1, c2, f2) to avoid duplicates

    for i, (concept1, word1) in enumerate(all_pairs):
        for j, (concept2, word2) in enumerate(all_pairs):
            if i >= j:  # Skip self and already-checked pairs
                continue
            if concept1 == concept2:  # Skip same concept
                continue

            # Check IPA similarity
            similarity = SequenceMatcher(None, word1.ipa, word2.ipa).ratio()
            if similarity >= 0.85:
                # Create canonical pair key to avoid duplicates
                pair_key = tuple(
                    sorted([(concept1, word1.form), (concept2, word2.form)])
                )
                flat_key = (
                    pair_key[0][0],
                    pair_key[0][1],
                    pair_key[1][0],
                    pair_key[1][1],
                )

                if flat_key not in seen_pairs:
                    seen_pairs.add(flat_key)
                    near_collisions.append(
                        {
                            "pair": [
                                {
                                    "concept": concept1,
                                    "form": word1.form,
                                    "ipa": word1.ipa,
                                },
                                {
                                    "concept": concept2,
                                    "form": word2.form,
                                    "ipa": word2.ipa,
                                },
                            ],
                            "similarity": round(similarity, 3),
                            "type": "ipa",
                        }
                    )

    # === WITHIN-CONCEPT COLLISIONS ===
    for concept_name, words in results.items():
        seen_within: Set[Tuple[str, str]] = set()  # (form1, form2) to avoid duplicates

        for i, word1 in enumerate(words):
            for j, word2 in enumerate(words):
                if i >= j:  # Skip self and already-checked pairs
                    continue

                # Check exact form match
                if word1.form.lower().strip() == word2.form.lower().strip():
                    sorted_forms = sorted([word1.form, word2.form])
                    pair_key = (sorted_forms[0], sorted_forms[1])
                    if pair_key not in seen_within:
                        seen_within.add(pair_key)
                        within_concept_collisions.append(
                            {
                                "concept": concept_name,
                                "forms": [word1.form, word2.form],
                                "similarity": 1.0,
                                "type": "exact_form",
                            }
                        )
                else:
                    # Check IPA similarity
                    similarity = SequenceMatcher(None, word1.ipa, word2.ipa).ratio()
                    if similarity >= 0.85:
                        sorted_forms = sorted([word1.form, word2.form])
                        pair_key = (sorted_forms[0], sorted_forms[1])
                        if pair_key not in seen_within:
                            seen_within.add(pair_key)
                            within_concept_collisions.append(
                                {
                                    "concept": concept_name,
                                    "forms": [word1.form, word2.form],
                                    "similarity": round(similarity, 3),
                                    "type": "ipa",
                                }
                            )

    return {
        "exact_collisions": exact_collisions,
        "near_collisions": near_collisions,
        "within_concept_collisions": within_concept_collisions,
    }
