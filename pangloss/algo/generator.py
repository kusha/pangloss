from dataclasses import dataclass
from typing import List, Set, Any, Optional
import networkx as nx
from pangloss.algo.convergence import ConvergencePoint


@dataclass
class SyntheticWord:
    phonemes: List[str]
    ipa: str
    form: str
    covered_languages: Set[str]
    speaker_count: int
    coverage_pct: float
    reasoning: str


def get_transliteration(phonemes: List[str]) -> str:
    mapping = {
        "ʂ": "sh",
        "ʃ": "sh",
        "tʃ": "ch",
        "dʒ": "j",
        "θ": "th",
        "ð": "th",
        "ŋ": "ng",
        "j": "y",
        "x": "kh",
        "ɣ": "gh",
        "ʔ": "",
        "c": "ch",
        "ɲ": "ny",
        "ʎ": "ly",
        "β": "v",
        "ɸ": "f",
        "ç": "sh",
        "ʁ": "r",
        "ʀ": "r",
        "ɾ": "r",
        "ɹ": "r",
        "ʋ": "v",
        "w": "w",
        "ʍ": "hw",
        "ɐ": "a",
        "ɑ": "a",
        "ɒ": "o",
        "æ": "a",
        "ə": "e",
        "ɛ": "e",
        "ɜ": "e",
        "ɪ": "i",
        "i": "i",
        "ɨ": "i",
        "ɔ": "o",
        "o": "o",
        "u": "u",
        "ʊ": "u",
        "ʌ": "a",
        "a": "a",
        "e": "e",
        "ː": "",
        "ʰ": "",
        "ʷ": "w",
        "ʲ": "y",
        "ˤ": "",
        "̃": "n",
        "ˈ": "",
        "ˌ": "",
    }
    result = []
    for p in phonemes:
        p_clean = p
        for char, repl in mapping.items():
            if char in p_clean:
                p_clean = p_clean.replace(char, repl)
        result.append(p_clean)

    raw_word = "".join(result)
    dedup = []
    for c in raw_word:
        if not dedup or dedup[-1] != c:
            dedup.append(c)
    return "".join(dedup)


def get_node_id(phonemes: List[str], reversed_seq: bool = False) -> str:
    if not phonemes:
        return "ε"
    seq = reversed(phonemes) if reversed_seq else phonemes
    return "-".join(seq)


def calculate_score(speakers: int, prefix_len: int, suffix_len: int) -> float:
    length = prefix_len + suffix_len
    return speakers / (1.0 + 0.5 * length)


def generate_word(
    convergence_point: ConvergencePoint,
    prefix_trie: nx.DiGraph,
    suffix_trie: nx.DiGraph,
    entries: List[Any],
    total_speakers: int,
    max_word_length: int = 8,
) -> SyntheticWord:
    total_world_speakers = total_speakers
    lang_speakers = {e.language_id: e.speaker_count for e in entries}

    current_prefix = list(convergence_point.prefix_phonemes)
    current_suffix = list(convergence_point.suffix_phonemes)

    reasoning_steps = []

    def get_intersection(p_seq: List[str], s_seq: List[str]):
        p_id = get_node_id(p_seq)
        s_id = get_node_id(s_seq, reversed_seq=True)
        p_langs = (
            prefix_trie.nodes[p_id]["languages"]
            if prefix_trie.has_node(p_id)
            else set()
        )
        s_langs = (
            suffix_trie.nodes[s_id]["languages"]
            if suffix_trie.has_node(s_id)
            else set()
        )
        if p_id == "ε":
            p_langs = set(lang_speakers.keys())
        if s_id == "ε":
            s_langs = set(lang_speakers.keys())

        intersect = p_langs & s_langs
        speakers = sum(lang_speakers.get(l, 0) for l in intersect)
        return intersect, speakers

    curr_langs, curr_speakers = get_intersection(current_prefix, current_suffix)
    curr_score = calculate_score(
        curr_speakers, len(current_prefix), len(current_suffix)
    )

    core_p = "/" + "-".join(current_prefix) + "/" if current_prefix else "ε"
    core_s = "/" + "-".join(current_suffix) + "/" if current_suffix else "ε"
    reasoning_steps.append(
        f"Core {core_p} + {core_s} covers {curr_speakers:,} speakers across {len(curr_langs)} languages."
    )

    # 1. LEFT EXTENSION: Grow prefix to make word more distinctive
    while len(current_prefix) + len(current_suffix) < max_word_length:
        p_id = get_node_id(current_prefix)
        if not prefix_trie.has_node(p_id):
            break

        best_child_phoneme = None
        best_child_score = -1
        best_child_langs = set()
        best_child_speakers = 0

        for child_id in prefix_trie.successors(p_id):
            phoneme = prefix_trie.edges[p_id, child_id]["phoneme"]

            # Anti-overlap: don't append if it's the first phoneme of the suffix
            if len(current_suffix) > 0 and phoneme == current_suffix[0]:
                continue

            child_prefix = current_prefix + [phoneme]
            new_langs, new_speakers = get_intersection(child_prefix, current_suffix)
            new_score = calculate_score(
                new_speakers, len(child_prefix), len(current_suffix)
            )

            if new_score > best_child_score:
                best_child_score = new_score
                best_child_phoneme = phoneme
                best_child_langs = new_langs
                best_child_speakers = new_speakers

        if best_child_phoneme and best_child_score > curr_score:
            current_prefix = current_prefix + [best_child_phoneme]
            curr_langs = best_child_langs
            curr_speakers = best_child_speakers
            curr_score = best_child_score
            reasoning_steps.append(
                f"Extended left with /{best_child_phoneme}/ to improve distinctiveness (score: {curr_score:,.0f})."
            )
        else:
            break

    # 2. RIGHT EXTENSION: Grow suffix
    while len(current_prefix) + len(current_suffix) < max_word_length:
        s_id = get_node_id(current_suffix, reversed_seq=True)
        if not suffix_trie.has_node(s_id):
            break

        best_child_phoneme = None
        best_child_score = -1
        best_child_langs = set()
        best_child_speakers = 0

        for child_id in suffix_trie.successors(s_id):
            phoneme = suffix_trie.edges[s_id, child_id]["phoneme"]

            # Anti-overlap
            if len(current_prefix) > 0 and phoneme == current_prefix[-1]:
                continue

            child_suffix = [phoneme] + current_suffix
            new_langs, new_speakers = get_intersection(current_prefix, child_suffix)
            new_score = calculate_score(
                new_speakers, len(current_prefix), len(child_suffix)
            )

            if new_score > best_child_score:
                best_child_score = new_score
                best_child_phoneme = phoneme
                best_child_langs = new_langs
                best_child_speakers = new_speakers

        if best_child_phoneme and best_child_score > curr_score:
            current_suffix = [best_child_phoneme] + current_suffix
            curr_langs = best_child_langs
            curr_speakers = best_child_speakers
            curr_score = best_child_score
            reasoning_steps.append(
                f"Extended right with /{best_child_phoneme}/ to improve distinctiveness (score: {curr_score:,.0f})."
            )
        else:
            break

    final_phonemes = current_prefix + current_suffix
    if not final_phonemes:
        final_phonemes = ["a"]

    ipa_str = f"/{''.join(final_phonemes)}/"
    trans_form = get_transliteration(final_phonemes)

    reasoning_steps.append(f"Final form: {ipa_str} (romanized: '{trans_form}').")

    return SyntheticWord(
        phonemes=final_phonemes,
        ipa=ipa_str,
        form=trans_form,
        covered_languages=curr_langs,
        speaker_count=curr_speakers,
        coverage_pct=(curr_speakers / total_world_speakers) * 100
        if total_world_speakers
        else 0.0,
        reasoning=" ".join(reasoning_steps),
    )
