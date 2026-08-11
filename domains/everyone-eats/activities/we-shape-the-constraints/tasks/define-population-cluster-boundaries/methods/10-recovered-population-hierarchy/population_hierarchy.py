"""Deterministic, evidence-safe core for building population hierarchy levels.

The recovered 2025 pipeline mixed two different objects: membership produced by
weighted k-means and display polygons produced by a separate Voronoi pass.  The
functions below keep the useful population-weighted grouping, but construct each
parent geometry from the exact union of its assigned children.  A parent can no
longer claim territory that its membership does not contain.

This module deliberately does not claim to enforce road travel or farm access.
Those constraints require versioned routing and land datasets plus measured
results.  They should enter as explicit, testable stages rather than comments or
straight-line proxies labeled as travel time.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import floor
from statistics import mean, median
from typing import Iterable, Sequence

import numpy as np
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


@dataclass(frozen=True)
class DemandUnit:
    """One indivisible child unit with an observed population."""

    unit_id: str
    population: int
    geometry: BaseGeometry
    households: int | None = None
    household_basis: str | None = None

    def __post_init__(self) -> None:
        if not self.unit_id:
            raise ValueError("unit_id is required")
        if self.population < 0:
            raise ValueError(f"{self.unit_id}: population cannot be negative")
        if self.geometry.is_empty or not self.geometry.is_valid:
            raise ValueError(f"{self.unit_id}: geometry must be non-empty and valid")
        if self.households is not None and self.households < 0:
            raise ValueError(f"{self.unit_id}: households cannot be negative")
        if self.households is not None and self.household_basis not in {
            "measured",
            "estimated",
        }:
            raise ValueError(
                f"{self.unit_id}: household_basis must be measured or estimated"
            )


@dataclass(frozen=True)
class LevelSpec:
    level: str
    target_population: int
    minimum_population: int
    maximum_population: int
    random_seed: int = 42
    max_iterations: int = 100

    def __post_init__(self) -> None:
        if not self.level:
            raise ValueError("level is required")
        if not 0 <= self.minimum_population <= self.target_population:
            raise ValueError("minimum_population must be between 0 and target")
        if self.maximum_population < self.target_population:
            raise ValueError("maximum_population must be at least target_population")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")


@dataclass(frozen=True)
class PopulationViolation:
    cluster_id: str
    rule: str
    actual_population: int
    limit: int


@dataclass(frozen=True)
class ParentCluster:
    cluster_id: str
    child_ids: tuple[str, ...]
    population: int
    households: int | None
    household_basis: str | None
    geometry: BaseGeometry


@dataclass(frozen=True)
class BuildResult:
    level: str
    projected_crs: str
    random_seed: int
    source_population: int
    clusters: tuple[ParentCluster, ...]
    violations: tuple[PopulationViolation, ...]

    def metrics(self) -> dict[str, int | float | str]:
        populations = [cluster.population for cluster in self.clusters]
        return {
            "level": self.level,
            "projected_crs": self.projected_crs,
            "random_seed": self.random_seed,
            "source_population": self.source_population,
            "cluster_count": len(populations),
            "mean_population": mean(populations),
            "median_population": median(populations),
            "minimum_population": min(populations),
            "maximum_population": max(populations),
            "violation_count": len(self.violations),
        }

    def require_publishable(self, waived_cluster_ids: Iterable[str] = ()) -> None:
        """Fail unless every population exception is explicitly waived."""

        waived = set(waived_cluster_ids)
        unresolved = [v for v in self.violations if v.cluster_id not in waived]
        unknown_waivers = waived - {v.cluster_id for v in self.violations}
        if unknown_waivers:
            raise ValueError(f"waivers do not match violations: {sorted(unknown_waivers)}")
        if unresolved:
            details = ", ".join(f"{v.cluster_id}:{v.rule}" for v in unresolved)
            raise ValueError(f"unresolved population violations: {details}")


def build_parent_level(
    units: Sequence[DemandUnit],
    spec: LevelSpec,
    *,
    projected_crs: str,
) -> BuildResult:
    """Group children and return exact, auditable parent geometries.

    Coordinates must already use a projected CRS suitable for distance work.
    The routine uses deterministic population-weighted k-means for membership.
    Population limits remain validation rules, not fictional guarantees.
    """

    if not units:
        raise ValueError("at least one demand unit is required")
    if not projected_crs or "4326" in projected_crs.upper():
        raise ValueError("provide an explicit projected CRS, not longitude/latitude")
    ids = [unit.unit_id for unit in units]
    if len(ids) != len(set(ids)):
        raise ValueError("unit_id values must be unique")

    source_population = sum(unit.population for unit in units)
    if source_population <= 0:
        raise ValueError("source population must be positive")

    cluster_count = _nearest_cluster_count(
        source_population, spec.target_population, len(units)
    )
    points = np.array(
        [
            [unit.geometry.representative_point().x, unit.geometry.representative_point().y]
            for unit in units
        ],
        dtype=float,
    )
    weights = np.array([max(unit.population, 1) for unit in units], dtype=float)
    labels = _weighted_kmeans(
        points,
        weights,
        cluster_count,
        random_seed=spec.random_seed,
        max_iterations=spec.max_iterations,
    )

    clusters = tuple(
        _make_parent(spec.level, units, labels, label)
        for label in range(cluster_count)
    )
    _validate_membership_and_geometry(units, clusters)

    violations: list[PopulationViolation] = []
    for cluster in clusters:
        if cluster.population < spec.minimum_population:
            violations.append(
                PopulationViolation(
                    cluster.cluster_id,
                    "below_minimum",
                    cluster.population,
                    spec.minimum_population,
                )
            )
        if cluster.population > spec.maximum_population:
            violations.append(
                PopulationViolation(
                    cluster.cluster_id,
                    "above_maximum",
                    cluster.population,
                    spec.maximum_population,
                )
            )

    return BuildResult(
        level=spec.level,
        projected_crs=projected_crs,
        random_seed=spec.random_seed,
        source_population=source_population,
        clusters=clusters,
        violations=tuple(violations),
    )


def _nearest_cluster_count(total: int, target: int, unit_count: int) -> int:
    """Choose the integer count whose global mean is closest to the target."""

    return min(unit_count, max(1, floor(total / target + 0.5)))


def _weighted_kmeans(
    points: np.ndarray,
    weights: np.ndarray,
    cluster_count: int,
    *,
    random_seed: int,
    max_iterations: int,
) -> np.ndarray:
    rng = np.random.default_rng(random_seed)
    centers = _weighted_kmeans_plus_plus(points, weights, cluster_count, rng)
    labels = np.full(len(points), -1, dtype=int)

    for _ in range(max_iterations):
        squared_distance = ((points[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        next_labels = squared_distance.argmin(axis=1)
        next_labels = _repair_empty_clusters(next_labels, squared_distance, weights)
        next_centers = np.vstack(
            [
                np.average(points[next_labels == label], axis=0, weights=weights[next_labels == label])
                for label in range(cluster_count)
            ]
        )
        if np.array_equal(labels, next_labels) or np.allclose(centers, next_centers):
            labels = next_labels
            break
        labels, centers = next_labels, next_centers

    if set(labels.tolist()) != set(range(cluster_count)):
        raise RuntimeError("clustering produced an empty parent")
    return labels


def _weighted_kmeans_plus_plus(
    points: np.ndarray,
    weights: np.ndarray,
    cluster_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    selected: list[int] = [int(rng.choice(len(points), p=weights / weights.sum()))]
    while len(selected) < cluster_count:
        squared = ((points[:, None, :] - points[selected][None, :, :]) ** 2).sum(axis=2)
        score = weights * squared.min(axis=1)
        score[selected] = 0
        remaining = np.flatnonzero(score > 0)
        if len(remaining) == 0:
            remaining = np.array([i for i in range(len(points)) if i not in selected])
            next_index = int(remaining[0])
        else:
            next_index = int(rng.choice(len(points), p=score / score.sum()))
        selected.append(next_index)
    return points[selected].copy()


def _repair_empty_clusters(
    labels: np.ndarray,
    squared_distance: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    labels = labels.copy()
    counts = np.bincount(labels, minlength=squared_distance.shape[1])
    for empty_label in np.flatnonzero(counts == 0):
        assigned_distance = squared_distance[np.arange(len(labels)), labels]
        candidates = np.flatnonzero(counts[labels] > 1)
        if len(candidates) == 0:
            raise RuntimeError("cannot repair empty cluster")
        moved_index = int(candidates[np.argmax(assigned_distance[candidates] * weights[candidates])])
        counts[labels[moved_index]] -= 1
        labels[moved_index] = empty_label
        counts[empty_label] += 1
    return labels


def _make_parent(
    level: str,
    units: Sequence[DemandUnit],
    labels: np.ndarray,
    label: int,
) -> ParentCluster:
    children = [unit for unit, assigned in zip(units, labels, strict=True) if assigned == label]
    child_ids = tuple(sorted(unit.unit_id for unit in children))
    digest = sha256(f"{level}|{'|'.join(child_ids)}".encode()).hexdigest()[:12]
    household_values = [unit.households for unit in children]
    households = None if any(value is None for value in household_values) else sum(household_values)  # type: ignore[arg-type]
    bases = {unit.household_basis for unit in children if unit.households is not None}
    household_basis = bases.pop() if len(bases) == 1 else ("mixed" if bases else None)
    return ParentCluster(
        cluster_id=f"{level}-{digest}",
        child_ids=child_ids,
        population=sum(unit.population for unit in children),
        households=households,
        household_basis=household_basis,
        geometry=unary_union([unit.geometry for unit in children]),
    )


def _validate_membership_and_geometry(
    units: Sequence[DemandUnit], clusters: Sequence[ParentCluster]
) -> None:
    expected_ids = sorted(unit.unit_id for unit in units)
    assigned_ids = sorted(child for cluster in clusters for child in cluster.child_ids)
    if assigned_ids != expected_ids:
        raise RuntimeError("every child must belong to exactly one parent")
    if sum(cluster.population for cluster in clusters) != sum(unit.population for unit in units):
        raise RuntimeError("population was not conserved")

    by_id = {unit.unit_id: unit for unit in units}
    for cluster in clusters:
        expected_geometry = unary_union([by_id[child].geometry for child in cluster.child_ids])
        if not cluster.geometry.equals(expected_geometry):
            raise RuntimeError(f"{cluster.cluster_id}: parent geometry differs from child union")
