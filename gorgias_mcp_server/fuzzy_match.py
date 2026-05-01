"""Tiered fuzzy matching used by smart-search to map free-text queries to
reference items (views, customer names, etc.).

Mirrors benpalmer1/Gorgias-MCP-Server's `src/fuzzy-match.ts` — Levenshtein
distance with a 7-tier scoring ladder so exact / prefix / multi-word matches
beat edit-distance fallbacks.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class FuzzyMatch(Generic[T]):
    item: T
    score: float


def _normalise(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.lower().strip())


def _split_words(text: str) -> list[str]:
    return [w for w in text.split(" ") if w]


def levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    m, n = len(a), len(b)
    dp: list[list[int]] = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1],  # substitution
                )
    return dp[m][n]


def _compute_score(
    norm_query: str,
    query_words: list[str],
    norm_candidate: str,
    candidate_words: list[str],
) -> float:
    # Tier 1: exact normalised match
    if norm_query == norm_candidate:
        return 100

    # Tier 2: candidate starts with query
    if norm_candidate.startswith(norm_query):
        return 80

    # Tier 3: every query word found in candidate words
    query_in_candidate = [
        qw for qw in query_words if any(cw == qw for cw in candidate_words)
    ]
    if len(query_in_candidate) == len(query_words):
        return 65 + (len(query_in_candidate) / len(candidate_words)) * 14

    # Tier 4: every candidate word found in query words
    candidate_in_query = [
        cw for cw in candidate_words if any(qw == cw for qw in query_words)
    ]
    if len(candidate_in_query) == len(candidate_words):
        return 50 + (len(candidate_in_query) / len(query_words)) * 14

    # Tier 5: per-word edit distance for multi-word queries
    if len(query_words) > 1:
        if all(
            any(levenshtein_distance(qw, cw) <= 2 for cw in candidate_words)
            for qw in query_words
        ):
            return 50

    # Tier 6: partial word overlap
    matching = sum(
        1 for qw in query_words if any(cw == qw for cw in candidate_words)
    )
    max_words = max(len(query_words), len(candidate_words))
    if matching > 0:
        return (matching / max_words) * 50

    # Tier 7: whole-string edit distance
    distance = levenshtein_distance(norm_query, norm_candidate)
    max_len = max(len(norm_query), len(norm_candidate))
    if max_len <= 5 and distance <= 2:
        return 45
    if max_len > 5 and distance <= 2:
        return 40

    # Tier 8: no match
    return 0


def fuzzy_match_name(
    query: str,
    candidates: list[T],
    get_name: Callable[[T], str],
    min_score: float = 40,
) -> list[FuzzyMatch[T]]:
    """Score each candidate by name similarity to the query and return matches >= min_score."""
    norm_query = _normalise(query)
    query_words = _split_words(norm_query)
    if not query_words:
        return []

    results: list[FuzzyMatch[T]] = []
    for item in candidates:
        name = get_name(item)
        norm_name = _normalise(name)
        candidate_words = _split_words(norm_name)
        if not candidate_words:
            continue

        score = _compute_score(norm_query, query_words, norm_name, candidate_words)
        if score >= min_score:
            results.append(FuzzyMatch(item=item, score=score))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
