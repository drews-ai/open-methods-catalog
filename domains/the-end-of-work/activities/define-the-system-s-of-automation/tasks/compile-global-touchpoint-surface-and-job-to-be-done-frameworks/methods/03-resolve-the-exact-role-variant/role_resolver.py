"""Deterministic exact-role resolver for the EndWork public method.

The resolver accepts already source-registered role aliases and facets. It never invents
an occupational identity, performs fuzzy matching, or silently selects among ambiguous
roles. Source acquisition, licensing, and taxonomy semantics remain upstream concerns.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
import math
import re
import unicodedata


_SPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w+#.'-]+", re.UNICODE)


def normalize_title(value: str) -> str:
    """Return a conservative matching key while leaving source labels untouched."""

    text = unicodedata.normalize("NFKC", value).casefold().strip()
    text = text.replace("&", " and ")
    text = _PUNCTUATION.sub(" ", text)
    return _SPACE.sub(" ", text).strip(" .'-")


@dataclass(frozen=True)
class Alias:
    label: str
    role_id: str
    source_id: str
    match_kind: str = "official_alias"


@dataclass(frozen=True)
class Candidate:
    role_id: str
    matched_label: str
    source_id: str
    match_kind: str


@dataclass(frozen=True)
class Resolution:
    status: str
    query: str
    normalized_query: str
    candidates: tuple[Candidate, ...]
    applied_answers: tuple[tuple[str, str], ...] = ()
    next_facet: str | None = None
    allowed_values: tuple[str, ...] = ()

    @property
    def role_id(self) -> str | None:
        if self.status == "resolved" and len(self.candidates) == 1:
            return self.candidates[0].role_id
        return None


class RoleResolver:
    """Resolve exact aliases, then reduce ambiguity through registered role facets."""

    def __init__(
        self,
        aliases: Iterable[Alias],
        facets: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        by_key: dict[str, list[Alias]] = defaultdict(list)
        seen: set[tuple[str, str, str, str]] = set()
        for alias in aliases:
            key = normalize_title(alias.label)
            if not key or not alias.role_id or not alias.source_id:
                raise ValueError("aliases require label, role_id, and source_id")
            identity = (key, alias.role_id, alias.source_id, alias.match_kind)
            if identity not in seen:
                by_key[key].append(alias)
                seen.add(identity)
        self._aliases = {
            key: tuple(sorted(values, key=lambda a: (a.role_id, a.source_id, a.label)))
            for key, values in by_key.items()
        }
        self._facets = {
            role_id: {axis: value for axis, value in values.items() if value}
            for role_id, values in (facets or {}).items()
        }

    def resolve(
        self,
        query: str,
        answers: Mapping[str, str] | None = None,
    ) -> Resolution:
        key = normalize_title(query)
        matched = self._aliases.get(key, ())
        if not matched:
            return Resolution("unsupported", query, key, ())

        candidates = self._collapse_candidates(matched)
        applied: list[tuple[str, str]] = []
        for axis, expected in sorted((answers or {}).items()):
            expected_key = normalize_title(expected)
            filtered = tuple(
                candidate
                for candidate in candidates
                if normalize_title(self._facets.get(candidate.role_id, {}).get(axis, ""))
                == expected_key
            )
            if filtered:
                candidates = filtered
                applied.append((axis, expected))

        if len(candidates) == 1:
            return Resolution("resolved", query, key, candidates, tuple(applied))

        next_facet = self._choose_facet([candidate.role_id for candidate in candidates])
        if next_facet is None:
            return Resolution("ambiguous", query, key, candidates, tuple(applied))

        values = tuple(
            sorted({self._facets[candidate.role_id][next_facet] for candidate in candidates})
        )
        return Resolution(
            "needs_fact",
            query,
            key,
            candidates,
            tuple(applied),
            next_facet,
            values,
        )

    @staticmethod
    def _collapse_candidates(aliases: Sequence[Alias]) -> tuple[Candidate, ...]:
        by_role: dict[str, Alias] = {}
        for alias in aliases:
            by_role.setdefault(alias.role_id, alias)
        return tuple(
            Candidate(role_id, alias.label, alias.source_id, alias.match_kind)
            for role_id, alias in sorted(by_role.items())
        )

    def _choose_facet(self, role_ids: Sequence[str]) -> str | None:
        axes = sorted({axis for role_id in role_ids for axis in self._facets.get(role_id, {})})
        scored: list[tuple[float, float, str]] = []
        for axis in axes:
            values = [self._facets.get(role_id, {}).get(axis) for role_id in role_ids]
            if any(not value for value in values) or len(set(values)) < 2:
                continue
            groups: dict[str, int] = defaultdict(int)
            for value in values:
                groups[str(value)] += 1
            expected_remaining = sum(size * size for size in groups.values()) / len(values)
            entropy = -sum(
                (size / len(values)) * math.log2(size / len(values))
                for size in groups.values()
            )
            scored.append((expected_remaining, -entropy, axis))
        return min(scored)[2] if scored else None

    def metrics(self) -> dict[str, float | int]:
        """Return structural alias ambiguity metrics without claiming accuracy."""

        fanouts = [len({alias.role_id for alias in aliases}) for aliases in self._aliases.values()]
        if not fanouts:
            return {
                "distinct_aliases": 0,
                "unique_aliases": 0,
                "ambiguous_aliases": 0,
                "unique_at_entry_pct": 0.0,
                "max_fanout": 0,
            }
        unique = sum(fanout == 1 for fanout in fanouts)
        return {
            "distinct_aliases": len(fanouts),
            "unique_aliases": unique,
            "ambiguous_aliases": sum(fanout > 1 for fanout in fanouts),
            "unique_at_entry_pct": round(100.0 * unique / len(fanouts), 1),
            "max_fanout": max(fanouts),
        }
