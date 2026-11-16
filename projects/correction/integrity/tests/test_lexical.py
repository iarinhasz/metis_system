import hashlib

import pytest

from projects.correction.integrity.lexical import (
    find_lexical_overlaps,
    stable_hash,
    tokenize_words,
)


@pytest.mark.parametrize("word_count", [6, 9])
def test_finds_common_passage_at_and_above_winnowing_threshold(word_count: int) -> None:
    k, w = 3, 4
    passage_words = [
        "amber",
        "birch",
        "cobalt",
        "daisy",
        "ember",
        "fjord",
        "garnet",
        "harbor",
        "indigo",
    ][:word_count]
    passage = " ".join(passage_words)
    source = f"Source prelude. {passage} Source suffix."
    target = f"Target opening! {passage} Target suffix."

    overlaps = find_lexical_overlaps(source, target, k=k, w=w)

    assert len(overlaps) == 1
    overlap = overlaps[0]
    assert source[overlap.source_start : overlap.source_end] == passage
    assert target[overlap.target_start : overlap.target_end] == passage
    assert word_count >= w + k - 1


def test_texts_without_a_relevant_common_passage_have_no_overlap() -> None:
    source = "alpha bravo charlie delta echo foxtrot"
    target = "golf hotel india juliet kilo lima"

    assert find_lexical_overlaps(source, target, k=3, w=4) == []


def test_hash_is_stable_blake2b_64_bit() -> None:
    words = ("alpha", "bravo", "charlie")
    expected = int.from_bytes(
        hashlib.blake2b("\0".join(words).encode("utf-8"), digest_size=8).digest(),
        "big",
    )

    assert stable_hash(words) == expected
    assert stable_hash(words) == stable_hash(words)


def test_case_and_punctuation_are_ignored_but_offsets_point_to_original_text() -> None:
    source = "Before: Alpha, BRAVO—charlie delta echo foxtrot golf! after."
    target = "Different: alpha bravo, CHARLIE; delta echo foxtrot golf? end."

    overlap = find_lexical_overlaps(source, target, k=3, w=3)[0]
    source_excerpt = source[overlap.source_start : overlap.source_end]
    target_excerpt = target[overlap.target_start : overlap.target_end]

    assert [token.value for token in tokenize_words(source_excerpt)] == [
        token.value for token in tokenize_words(target_excerpt)
    ]
    assert source_excerpt == "Alpha, BRAVO—charlie delta echo foxtrot golf"
    assert target_excerpt == "alpha bravo, CHARLIE; delta echo foxtrot golf"


def test_finds_multiple_copied_passages_in_one_document() -> None:
    first = "amber birch cobalt daisy ember fjord"
    second = "garnet harbor indigo juniper keystone lantern"
    source = f"source begins {first} unrelated words here {second} source ends"
    target = f"target opens {first} other text there {second} target ends"

    overlaps = find_lexical_overlaps(source, target, k=3, w=3)

    assert len(overlaps) == 2
    assert [source[item.source_start : item.source_end] for item in overlaps] == [first, second]
    assert [target[item.target_start : item.target_end] for item in overlaps] == [first, second]


def test_rejects_invalid_shingle_and_window_sizes() -> None:
    with pytest.raises(ValueError, match="k"):
        find_lexical_overlaps("text", "text", k=0)
    with pytest.raises(ValueError, match="w"):
        find_lexical_overlaps("text", "text", w=0)
