"""Validated, advisory value-flow resolver for an EndWork Method.

The resolver reads one released graph and optional detail files. It performs no work,
grants no authority, and writes no event. Callers decide what to do and append resulting
events through the accepted ledger release.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


class FlowValidationError(ValueError):
    """The released graph violates the public value-flow contract."""


class UnsafeDetailReference(FlowValidationError):
    """A detail reference escapes or cannot be resolved inside the release root."""


VIEW_FIELDS = (
    "id",
    "title",
    "kind",
    "parent_id",
    "order",
    "canonical_id",
    "rea",
    "loop",
    "gate",
    "derive",
    "automation",
    "confidence",
)


def _node_view(node: Mapping[str, Any]) -> dict[str, Any]:
    return {field: node.get(field) for field in VIEW_FIELDS}


@dataclass(frozen=True)
class ValueFlow:
    release_root: Path
    graph: Mapping[str, Any]

    @classmethod
    def load(cls, release_root: str | Path, graph_path: str | Path) -> "ValueFlow":
        root = Path(release_root).resolve(strict=True)
        path = Path(graph_path).resolve(strict=True)
        if not path.is_relative_to(root):
            raise FlowValidationError("graph path escapes the declared release root")
        with path.open(encoding="utf-8") as handle:
            graph = json.load(handle)
        validate_graph(graph)
        return cls(root, graph)

    @property
    def nodes(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.graph["nodes"])

    @property
    def index(self) -> dict[str, Mapping[str, Any]]:
        return {node["id"]: node for node in self.nodes}

    def root(self) -> dict[str, Any]:
        root = next(node for node in self.nodes if not node.get("parent_id"))
        children = self._ordered_children(root)
        return {
            "domain": self.graph.get("domain"),
            "version": self.graph.get("version"),
            "root": _node_view(root),
            "children": [_node_view(child) for child in children],
        }

    def get(self, node_id: str) -> dict[str, Any]:
        node = self.index.get(node_id)
        if node is None:
            return {"status": "unsupported", "node_id": node_id}
        return {"status": "found", "node": _node_view(node)}

    def expand(self, node_id: str) -> dict[str, Any]:
        node = self.index.get(node_id)
        if node is None:
            return {"status": "unsupported", "node_id": node_id, "children": []}
        return {
            "status": "found",
            "node_id": node_id,
            "title": node["title"],
            "children": [_node_view(child) for child in self._ordered_children(node)],
        }

    def detail(self, node_id: str, max_bytes: int = 16_000) -> dict[str, Any]:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        node = self.index.get(node_id)
        if node is None:
            return {"status": "unsupported", "node_id": node_id, "details": []}
        details = []
        for reference in node.get("detail_refs") or []:
            relative_path = str(reference).split("#", 1)[0]
            try:
                detail_path = (self.release_root / relative_path).resolve(strict=True)
            except FileNotFoundError as error:
                raise UnsafeDetailReference(f"missing detail reference: {reference}") from error
            if not detail_path.is_relative_to(self.release_root) or not detail_path.is_file():
                raise UnsafeDetailReference(f"unsafe detail reference: {reference}")
            payload = detail_path.read_bytes()[:max_bytes]
            details.append(
                {
                    "reference": reference,
                    "bytes_returned": len(payload),
                    "truncated": detail_path.stat().st_size > len(payload),
                    "excerpt": payload.decode("utf-8", errors="replace"),
                }
            )
        return {
            "status": "found",
            "node": _node_view(node),
            "instructions": node.get("how"),
            "sources": node.get("sources") or [],
            "details": details,
        }

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        if limit < 1:
            raise ValueError("limit must be positive")
        words = tuple(word for word in query.casefold().split() if word)
        scored = []
        for node in self.nodes:
            title = str(node.get("title") or "").casefold()
            haystack = " ".join(
                (
                    title,
                    str(node.get("how") or "").casefold(),
                    str(node.get("canonical_id") or "").casefold(),
                )
            )
            score = sum(haystack.count(word) for word in words)
            score += 3 * sum(word in title for word in words)
            if score:
                scored.append((score, str(node["id"]), node))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return {
            "query": query,
            "matches": [
                {**_node_view(node), "score": score}
                for score, _, node in scored[:limit]
            ],
        }

    def deviation_record(
        self,
        node_id: str,
        action: str,
        reason: str,
        occurred_at: str,
    ) -> dict[str, str]:
        if node_id not in self.index:
            raise FlowValidationError(f"unknown deviation node: {node_id}")
        if not action.strip() or not reason.strip() or not occurred_at.strip():
            raise FlowValidationError("deviation action, reason, and occurred_at are required")
        return {
            "event_type": "value_flow.deviation_recorded",
            "flow_domain": str(self.graph.get("domain") or ""),
            "flow_version": str(self.graph.get("version") or ""),
            "node_id": node_id,
            "action": action,
            "reason": reason,
            "occurred_at": occurred_at,
        }

    def _ordered_children(self, node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return sorted(
            (self.index[child_id] for child_id in node.get("children") or []),
            key=lambda child: (child.get("order", 0), child["id"]),
        )


def validate_graph(graph: Mapping[str, Any]) -> None:
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise FlowValidationError("nodes must be a non-empty list")

    ids = []
    for position, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise FlowValidationError(f"node {position} must be an object")
        for field in ("id", "title", "kind"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                raise FlowValidationError(f"node {position} requires non-empty {field}")
        ids.append(node["id"])

    if len(ids) != len(set(ids)):
        raise FlowValidationError("node ids must be unique")
    index = {node["id"]: node for node in nodes}
    roots = [node for node in nodes if not node.get("parent_id")]
    if len(roots) != 1:
        raise FlowValidationError("graph must contain exactly one root")

    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id and parent_id not in index:
            raise FlowValidationError(f"unknown parent {parent_id} for {node['id']}")

    for node in nodes:
        children = node.get("children") or []
        if not isinstance(children, list) or any(child not in index for child in children):
            raise FlowValidationError(f"invalid child reference for {node['id']}")
        for child_id in children:
            if index[child_id].get("parent_id") != node["id"]:
                raise FlowValidationError(f"parent-child disagreement for {child_id}")

    for node_id in ids:
        seen = set()
        cursor = node_id
        while cursor:
            if cursor in seen:
                raise FlowValidationError(f"parent cycle includes {cursor}")
            seen.add(cursor)
            cursor = index[cursor].get("parent_id")
