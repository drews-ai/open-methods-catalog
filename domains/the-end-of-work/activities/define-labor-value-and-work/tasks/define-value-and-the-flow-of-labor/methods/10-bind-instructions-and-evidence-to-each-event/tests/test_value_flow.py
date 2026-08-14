from pathlib import Path
import json
import sys
import tempfile
import unittest


METHOD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(METHOD_DIR))

from value_flow import FlowValidationError, UnsafeDetailReference, ValueFlow  # noqa: E402


def graph_fixture():
    return {
        "domain": "fixture",
        "version": "fixture-v1",
        "nodes": [
            {
                "id": "work",
                "title": "Run the work",
                "kind": "root",
                "parent_id": None,
                "order": 0,
                "children": ["work.research", "work.review"],
            },
            {
                "id": "work.research",
                "title": "Research evidence",
                "kind": "event",
                "parent_id": "work",
                "order": 1,
                "children": [],
                "how": "Collect and register exact sources.",
                "canonical_id": "research-evidence",
                "detail_refs": ["details/research.md#procedure"],
                "sources": ["source-1"],
            },
            {
                "id": "work.review",
                "title": "Review evidence",
                "kind": "gate",
                "parent_id": "work",
                "order": 2,
                "children": [],
                "how": "Accept, reject, or hold each claim.",
                "canonical_id": "review-evidence",
            },
        ],
    }


class ValueFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "details").mkdir()
        (self.root / "details" / "research.md").write_text(
            "Collect the corpus, register each source, and preserve disagreements.",
            encoding="utf-8",
        )
        self.graph_path = self.root / "fixture.flow.json"
        self.graph_path.write_text(json.dumps(graph_fixture()), encoding="utf-8")
        self.flow = ValueFlow.load(self.root, self.graph_path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_root_and_children_are_ordered(self):
        result = self.flow.root()
        self.assertEqual(result["root"]["id"], "work")
        self.assertEqual(
            [child["id"] for child in result["children"]],
            ["work.research", "work.review"],
        )

    def test_unknown_nodes_remain_unsupported(self):
        self.assertEqual(self.flow.get("missing")["status"], "unsupported")
        self.assertEqual(self.flow.expand("missing")["children"], [])

    def test_detail_is_bounded_and_source_linked(self):
        result = self.flow.detail("work.research", max_bytes=20)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["sources"], ["source-1"])
        self.assertEqual(result["details"][0]["bytes_returned"], 20)
        self.assertTrue(result["details"][0]["truncated"])

    def test_detail_path_traversal_is_rejected(self):
        outside = self.root.parent / "outside-detail.txt"
        outside.write_text("private", encoding="utf-8")
        graph = graph_fixture()
        graph["nodes"][1]["detail_refs"] = ["../outside-detail.txt"]
        self.graph_path.write_text(json.dumps(graph), encoding="utf-8")
        flow = ValueFlow.load(self.root, self.graph_path)
        with self.assertRaises(UnsafeDetailReference):
            flow.detail("work.research")
        outside.unlink()

    def test_search_is_deterministic(self):
        result = self.flow.search("review evidence")
        self.assertEqual(result["matches"][0]["id"], "work.review")

    def test_deviation_is_returned_without_writing(self):
        result = self.flow.deviation_record(
            "work.review",
            "hold",
            "the source license is unresolved",
            "2026-08-14T12:00:00Z",
        )
        self.assertEqual(result["event_type"], "value_flow.deviation_recorded")
        self.assertEqual(list(self.root.glob("*.jsonl")), [])

    def test_duplicate_ids_fail_validation(self):
        graph = graph_fixture()
        graph["nodes"][2]["id"] = "work.research"
        self.graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(FlowValidationError, "unique"):
            ValueFlow.load(self.root, self.graph_path)

    def test_missing_parent_fails_validation(self):
        graph = graph_fixture()
        graph["nodes"][1]["parent_id"] = "missing"
        self.graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(FlowValidationError, "unknown parent"):
            ValueFlow.load(self.root, self.graph_path)

    def test_parent_cycle_fails_validation(self):
        graph = graph_fixture()
        graph["nodes"][0]["parent_id"] = "work.research"
        graph["nodes"][1]["children"] = ["work"]
        from value_flow import validate_graph

        with self.assertRaisesRegex(FlowValidationError, "one root"):
            validate_graph(graph)


if __name__ == "__main__":
    unittest.main()
