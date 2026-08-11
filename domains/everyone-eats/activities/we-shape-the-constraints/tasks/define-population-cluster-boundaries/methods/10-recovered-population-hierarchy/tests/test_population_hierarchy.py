from __future__ import annotations

import sys
import unittest
from pathlib import Path

from shapely.geometry import box
from shapely.ops import unary_union

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from population_hierarchy import DemandUnit, LevelSpec, build_parent_level  # noqa: E402


def make_units(populations: list[int]) -> list[DemandUnit]:
    return [
        DemandUnit(
            unit_id=f"block-{index}",
            population=population,
            geometry=box(index * 1_000, 0, index * 1_000 + 900, 900),
        )
        for index, population in enumerate(populations)
    ]


class PopulationHierarchyTests(unittest.TestCase):
    def test_build_is_deterministic_and_conserves_population(self) -> None:
        units = make_units([100, 120, 80, 110, 90, 105, 95, 100])
        spec = LevelSpec("L1", 200, 75, 325, random_seed=7)

        first = build_parent_level(units, spec, projected_crs="EPSG:5070")
        second = build_parent_level(units, spec, projected_crs="EPSG:5070")

        self.assertEqual(
            [cluster.cluster_id for cluster in first.clusters],
            [cluster.cluster_id for cluster in second.clusters],
        )
        self.assertEqual(first.source_population, 800)
        self.assertEqual(sum(cluster.population for cluster in first.clusters), 800)
        self.assertEqual(len(first.clusters), 4)

    def test_every_child_is_assigned_once(self) -> None:
        units = make_units([75, 100, 125, 150, 175, 200])
        result = build_parent_level(
            units,
            LevelSpec("L1", 275, 50, 500),
            projected_crs="ESRI:102003",
        )

        assigned = [child for cluster in result.clusters for child in cluster.child_ids]
        self.assertCountEqual(assigned, [unit.unit_id for unit in units])
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_parent_geometry_is_the_union_of_its_children(self) -> None:
        units = make_units([100, 100, 100, 100])
        result = build_parent_level(
            units,
            LevelSpec("L1", 200, 50, 350),
            projected_crs="EPSG:5070",
        )
        by_id = {unit.unit_id: unit for unit in units}

        for cluster in result.clusters:
            expected = unary_union([by_id[child].geometry for child in cluster.child_ids])
            self.assertTrue(cluster.geometry.equals(expected))

    def test_longitude_latitude_crs_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "projected CRS"):
            build_parent_level(
                make_units([100, 100]),
                LevelSpec("L1", 200, 50, 300),
                projected_crs="EPSG:4326",
            )

    def test_population_exceptions_require_explicit_waivers(self) -> None:
        result = build_parent_level(
            make_units([1_000, 1, 1]),
            LevelSpec("L1", 501, 1, 600),
            projected_crs="EPSG:5070",
        )

        self.assertEqual(len(result.violations), 1)
        with self.assertRaisesRegex(ValueError, "unresolved population violations"):
            result.require_publishable()
        result.require_publishable([result.violations[0].cluster_id])

    def test_estimated_households_cannot_masquerade_as_measured(self) -> None:
        units = [
            DemandUnit("a", 250, box(0, 0, 1, 1), 100, "estimated"),
            DemandUnit("b", 250, box(1, 0, 2, 1), 100, "estimated"),
        ]
        result = build_parent_level(
            units,
            LevelSpec("L0", 500, 100, 800),
            projected_crs="EPSG:5070",
        )

        self.assertEqual(result.clusters[0].households, 200)
        self.assertEqual(result.clusters[0].household_basis, "estimated")
        with self.assertRaisesRegex(ValueError, "household_basis"):
            DemandUnit("bad", 100, box(0, 0, 1, 1), 40)


if __name__ == "__main__":
    unittest.main()
