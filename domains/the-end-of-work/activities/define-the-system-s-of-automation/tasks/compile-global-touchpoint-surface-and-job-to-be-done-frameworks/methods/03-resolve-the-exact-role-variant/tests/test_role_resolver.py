from pathlib import Path
import sys
import unittest


METHOD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(METHOD_DIR))

from role_resolver import Alias, RoleResolver, normalize_title  # noqa: E402


ALIASES = [
    Alias("SEO Specialist", "13-1161", "onet-30.3"),
    Alias("Claims Adjuster", "13-1031", "onet-30.3"),
    Alias("Systems Analyst", "15-1211", "fixture"),
    Alias("Systems Analyst", "15-1299", "fixture"),
    Alias("Analyst", "13-1111", "fixture"),
    Alias("Analyst", "15-1211", "fixture"),
    Alias("Coordinator", "11-0001", "fixture"),
    Alias("Coordinator", "13-0001", "fixture"),
]

FACETS = {
    "13-1161": {"subcluster": "Marketing Research", "job_zone": "4"},
    "13-1031": {"subcluster": "Insurance", "job_zone": "4"},
    "15-1211": {"subcluster": "Information Technology", "job_zone": "4"},
    "15-1299": {"subcluster": "Information Technology", "job_zone": "3"},
    "13-1111": {"subcluster": "Management", "job_zone": "4"},
    "11-0001": {"subcluster": "Management"},
    "13-0001": {},
}


class RoleResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = RoleResolver(ALIASES, FACETS)

    def test_normalization_is_conservative_and_repeatable(self) -> None:
        self.assertEqual(normalize_title("  SEO & Search  "), "seo and search")
        self.assertEqual(normalize_title("Claims-Adjuster"), "claims-adjuster")

    def test_unique_exact_alias_resolves(self) -> None:
        result = self.resolver.resolve("seo specialist")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.role_id, "13-1161")

    def test_unknown_title_stays_unsupported(self) -> None:
        result = self.resolver.resolve("intergalactic workflow wizard")
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.candidates, ())

    def test_best_available_facet_is_requested(self) -> None:
        result = self.resolver.resolve("systems analyst")
        self.assertEqual(result.status, "needs_fact")
        self.assertEqual(result.next_facet, "job_zone")
        self.assertEqual(result.allowed_values, ("3", "4"))

    def test_answer_resolves_ambiguous_alias(self) -> None:
        result = self.resolver.resolve("systems analyst", {"job_zone": "3"})
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.role_id, "15-1299")

    def test_complete_facet_is_used_when_another_axis_is_incomplete(self) -> None:
        result = self.resolver.resolve("analyst")
        self.assertEqual(result.status, "needs_fact")
        self.assertEqual(result.next_facet, "subcluster")

    def test_missing_facet_preserves_ambiguity(self) -> None:
        result = self.resolver.resolve("coordinator")
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.next_facet)
        self.assertEqual({c.role_id for c in result.candidates}, {"11-0001", "13-0001"})

    def test_invalid_answer_does_not_erase_candidates(self) -> None:
        result = self.resolver.resolve("systems analyst", {"job_zone": "99"})
        self.assertEqual(result.status, "needs_fact")
        self.assertEqual(len(result.candidates), 2)

    def test_metrics_describe_structure_not_accuracy(self) -> None:
        metrics = self.resolver.metrics()
        self.assertEqual(metrics["distinct_aliases"], 5)
        self.assertEqual(metrics["unique_aliases"], 2)
        self.assertEqual(metrics["ambiguous_aliases"], 3)
        self.assertEqual(metrics["unique_at_entry_pct"], 40.0)
        self.assertEqual(metrics["max_fanout"], 2)


if __name__ == "__main__":
    unittest.main()
