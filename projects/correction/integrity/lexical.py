"""Detecção de trechos lexicais idênticos com MinHash-LSH e winnowing."""

from __future__ import annotations

import hashlib
import re
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from datasketch import MinHash, MinHashLSH  # type: ignore

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NUM_PERM = 128
_MINHASH_SEED = 1


@dataclass(frozen=True)
class WordToken:
    """Palavra normalizada e offsets de caracteres no texto original."""

    value: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
class LexicalOverlap:
    """Intervalos alinhados de um trecho lexical comum nos textos de origem e destino."""

    source_start: int
    source_end: int
    target_start: int
    target_end: int


@dataclass(frozen=True)
class _TokenSpan:
    source_start: int
    source_end: int
    target_start: int
    target_end: int


def tokenize_words(text: str) -> tuple[WordToken, ...]:
    """Tokeniza palavras sem perder seus offsets no texto original."""
    return tuple(
        WordToken(match.group().casefold(), match.start(), match.end())
        for match in _WORD.finditer(text)
    )


def stable_hash(words: Sequence[str]) -> int:
    """Hash determinístico de 64 bits de uma sequência de palavras normalizadas."""
    payload = "\0".join(words).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def _shingles(words: Sequence[str], k: int) -> Iterable[tuple[str, ...]]:
    return (tuple(words[index : index + k]) for index in range(len(words) - k + 1))


def _minhash(shingles: Iterable[tuple[str, ...]]) -> MinHash:
    signature = MinHash(num_perm=_NUM_PERM, seed=_MINHASH_SEED)
    for shingle in shingles:
        signature.update("\0".join(shingle).encode("utf-8"))
    return signature


def _winnow(words: Sequence[str], k: int, w: int) -> tuple[tuple[int, int], ...]:
    hashes = [stable_hash(words[index : index + k]) for index in range(len(words) - k + 1)]
    if not hashes:
        return ()

    selected: list[tuple[int, int]] = []
    minima: deque[int] = deque()
    last_selected = -1
    for index, value in enumerate(hashes):
        while minima and minima[0] <= index - w:
            minima.popleft()
        while minima and hashes[minima[-1]] >= value:
            minima.pop()
        minima.append(index)
        if index >= w - 1 and minima[0] != last_selected:
            last_selected = minima[0]
            selected.append((hashes[last_selected], last_selected))
    return tuple(selected)


def _expand_match(
    source_words: Sequence[str],
    target_words: Sequence[str],
    source_start: int,
    target_start: int,
    k: int,
) -> _TokenSpan | None:
    if (
        source_words[source_start : source_start + k]
        != target_words[target_start : target_start + k]
    ):
        return None

    while (
        source_start > 0
        and target_start > 0
        and source_words[source_start - 1] == target_words[target_start - 1]
    ):
        source_start -= 1
        target_start -= 1

    source_end = source_start + k
    target_end = target_start + k
    while (
        source_end < len(source_words)
        and target_end < len(target_words)
        and source_words[source_end] == target_words[target_end]
    ):
        source_end += 1
        target_end += 1
    return _TokenSpan(source_start, source_end, target_start, target_end)


def _merge_spans(spans: Iterable[_TokenSpan]) -> tuple[_TokenSpan, ...]:
    merged: list[_TokenSpan] = []
    for span in sorted(spans, key=lambda item: (item.source_start, item.target_start)):
        if not merged:
            merged.append(span)
            continue

        previous = merged[-1]
        same_alignment = (
            span.source_start - span.target_start == previous.source_start - previous.target_start
        )
        if (
            same_alignment
            and span.source_start <= previous.source_end
            and span.target_start <= previous.target_end
        ):
            merged[-1] = _TokenSpan(
                previous.source_start,
                max(previous.source_end, span.source_end),
                previous.target_start,
                max(previous.target_end, span.target_end),
            )
        else:
            merged.append(span)
    return tuple(merged)


def find_lexical_overlaps(
    source_text: str,
    target_text: str,
    *,
    k: int = 5,
    w: int = 4,
    lsh_threshold: float = 0.5,
) -> list[LexicalOverlap]:
    """Encontra trechos comuns com ao menos ``w + k - 1`` palavras e offsets exatos.

    MinHash-LSH recupera candidatos aproximados. A interseção direta dos fingerprints
    winnowed também seleciona o par para garantir recall no limite documentado.
    """
    if k < 1:
        raise ValueError("k deve ser maior que zero.")
    if w < 1:
        raise ValueError("w deve ser maior que zero.")
    if not 0 < lsh_threshold <= 1:
        raise ValueError("lsh_threshold deve estar no intervalo (0, 1].")

    source_tokens = tokenize_words(source_text)
    target_tokens = tokenize_words(target_text)
    source_words = tuple(token.value for token in source_tokens)
    target_words = tuple(token.value for token in target_tokens)
    source_shingles = tuple(_shingles(source_words, k))
    target_shingles = tuple(_shingles(target_words, k))
    if not source_shingles or not target_shingles:
        return []

    source_fingerprints = _winnow(source_words, k, w)
    target_fingerprints = _winnow(target_words, k, w)
    source_hashes = {fingerprint for fingerprint, _ in source_fingerprints}
    target_hashes = {fingerprint for fingerprint, _ in target_fingerprints}
    shared_fingerprints = source_hashes & target_hashes

    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=_NUM_PERM)
    lsh.insert("source", _minhash(source_shingles))
    lsh_candidates = bool(lsh.query(_minhash(target_shingles)))
    if not lsh_candidates and not shared_fingerprints:
        return []

    source_positions: dict[int, list[int]] = {}
    target_positions: dict[int, list[int]] = {}
    for fingerprint, position in source_fingerprints:
        if fingerprint in shared_fingerprints:
            source_positions.setdefault(fingerprint, []).append(position)
    for fingerprint, position in target_fingerprints:
        if fingerprint in shared_fingerprints:
            target_positions.setdefault(fingerprint, []).append(position)

    spans = (
        expanded
        for fingerprint in shared_fingerprints
        for source_position in source_positions[fingerprint]
        for target_position in target_positions[fingerprint]
        if (
            expanded := _expand_match(
                source_words,
                target_words,
                source_position,
                target_position,
                k,
            )
        )
        is not None
    )
    return [
        LexicalOverlap(
            source_start=source_tokens[span.source_start].start_char,
            source_end=source_tokens[span.source_end - 1].end_char,
            target_start=target_tokens[span.target_start].start_char,
            target_end=target_tokens[span.target_end - 1].end_char,
        )
        for span in _merge_spans(spans)
    ]
