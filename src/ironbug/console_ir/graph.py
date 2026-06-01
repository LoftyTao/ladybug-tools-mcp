"""Resolved graph contracts for Python Ironbug Console planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ironbug.console_ir.diagnostics import (
    PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
    ConsoleDiagnostic,
)


@dataclass(frozen=True)
class ConsoleGraphNode:
    """A resolved Ironbug source object in compiler graph form."""

    identifier: str
    source_class: str
    path: tuple[str, ...] = ()
    fields: Mapping[str, Any] = field(default_factory=dict)
    children: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("Python Console graph node identifier cannot be empty.")
        if not self.source_class:
            raise ValueError("Python Console graph node source_class cannot be empty.")
        object.__setattr__(self, "path", tuple(self.path))
        object.__setattr__(self, "fields", dict(self.fields))
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class ConsoleGraph:
    """A deterministic lookup surface for resolved Ironbug graph nodes."""

    nodes: tuple[ConsoleGraphNode, ...]

    @classmethod
    def from_nodes(cls, nodes: Iterable[ConsoleGraphNode]) -> "ConsoleGraph":
        node_tuple = tuple(nodes)
        identifiers: set[str] = set()
        for node in node_tuple:
            if node.identifier in identifiers:
                raise ValueError(
                    f"Duplicate Python Console graph node identifier: {node.identifier}"
                )
            identifiers.add(node.identifier)
        return cls(nodes=node_tuple)

    @property
    def source_classes(self) -> tuple[str, ...]:
        ordered_classes: list[str] = []
        seen_classes: set[str] = set()
        for node in self.nodes:
            if node.source_class not in seen_classes:
                ordered_classes.append(node.source_class)
                seen_classes.add(node.source_class)
        return tuple(ordered_classes)

    def node_by_identifier(self, identifier: str) -> ConsoleGraphNode:
        for node in self.nodes:
            if node.identifier == identifier:
                return node
        raise KeyError(f"Unknown Python Console graph node: {identifier}")

    def nodes_by_source_class(self, source_class: str) -> tuple[ConsoleGraphNode, ...]:
        return tuple(node for node in self.nodes if node.source_class == source_class)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "identifier": node.identifier,
                    "source_class": node.source_class,
                    "path": list(node.path),
                    "fields": dict(node.fields),
                    "children": list(node.children),
                }
                for node in self.nodes
            ],
            "source_classes": list(self.source_classes),
        }


@dataclass(frozen=True)
class ConsoleCompilePlan:
    """Compiler plan plus diagnostics before any runtime writer is invoked."""

    graph: ConsoleGraph
    diagnostics: tuple[ConsoleDiagnostic, ...] = ()
    writer_families: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "writer_families", tuple(self.writer_families))

    @property
    def blocked(self) -> bool:
        return any(diagnostic.severity == "error" for diagnostic in self.diagnostics)

    @classmethod
    def for_unsupported_source_class(
        cls,
        *,
        graph: ConsoleGraph,
        node_identifier: str,
        reason: str,
    ) -> "ConsoleCompilePlan":
        node = graph.node_by_identifier(node_identifier)
        diagnostic = ConsoleDiagnostic(
            code=PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
            message=(
                f"{node.source_class} is not supported by the Python Console: {reason}"
            ),
            source_class=node.source_class,
            identifier=node.identifier,
            path=node.path,
        )
        return cls(graph=graph, diagnostics=(diagnostic,))

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "writer_families": list(self.writer_families),
            "diagnostics": [
                diagnostic.to_dict() for diagnostic in self.diagnostics
            ],
            "graph": self.graph.to_dict(),
        }
