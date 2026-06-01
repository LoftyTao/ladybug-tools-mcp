"""Writer-family planning for the Python Ironbug Console."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ironbug.console_ir import (
    PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
    PYCONSOLE_WRITER_NOT_IMPLEMENTED,
    ConsoleDiagnostic,
    ConsoleGraph,
    ConsoleGraphNode,
)

from garden.ironbug_console.writer_registry_families import (
    FIRST_WRITER_FAMILY_NAMES,
    _FUTURE_SOURCE_CLASSES,
    _IMPLEMENTED_SOURCE_CLASSES,
    known_source_class_families,
)


@dataclass(frozen=True)
class ConsoleWriterNodePlan:
    """Writer-family route for one resolved graph node."""

    identifier: str
    source_class: str
    writer_family: str | None
    implemented: bool

    @classmethod
    def from_node(cls, node: ConsoleGraphNode) -> "ConsoleWriterNodePlan":
        if node.source_class in _IMPLEMENTED_SOURCE_CLASSES:
            return cls(
                identifier=node.identifier,
                source_class=node.source_class,
                writer_family=_IMPLEMENTED_SOURCE_CLASSES[node.source_class],
                implemented=True,
            )
        if node.source_class in _FUTURE_SOURCE_CLASSES:
            return cls(
                identifier=node.identifier,
                source_class=node.source_class,
                writer_family=_FUTURE_SOURCE_CLASSES[node.source_class],
                implemented=False,
            )
        return cls(
            identifier=node.identifier,
            source_class=node.source_class,
            writer_family=None,
            implemented=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "source_class": self.source_class,
            "writer_family": self.writer_family,
            "implemented": self.implemented,
        }


@dataclass(frozen=True)
class ConsoleWriterPlan:
    """Deterministic writer-family plan before runtime writing."""

    graph: ConsoleGraph
    node_plans: tuple[ConsoleWriterNodePlan, ...]
    diagnostics: tuple[ConsoleDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_plans", tuple(self.node_plans))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    @property
    def blocked(self) -> bool:
        return any(diagnostic.severity == "error" for diagnostic in self.diagnostics)

    @property
    def writer_families(self) -> tuple[str, ...]:
        present = {
            node_plan.writer_family
            for node_plan in self.node_plans
            if node_plan.implemented and node_plan.writer_family is not None
        }
        ordered = [
            family for family in FIRST_WRITER_FAMILY_NAMES if family in present
        ]
        extras = sorted(present - set(FIRST_WRITER_FAMILY_NAMES))
        return tuple([*ordered, *extras])

    def node_plan_by_identifier(self, identifier: str) -> ConsoleWriterNodePlan:
        for node_plan in self.node_plans:
            if node_plan.identifier == identifier:
                return node_plan
        raise KeyError(f"Unknown Python Console writer node plan: {identifier}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "writer_families": list(self.writer_families),
            "node_plans": [node_plan.to_dict() for node_plan in self.node_plans],
            "diagnostics": [
                diagnostic.to_dict() for diagnostic in self.diagnostics
            ],
        }


def build_writer_family_plan(graph: ConsoleGraph) -> ConsoleWriterPlan:
    """Map source-compatible graph classes to current writer-family contracts."""

    node_plans = tuple(
        ConsoleWriterNodePlan.from_node(node) for node in graph.nodes
    )
    diagnostics = tuple(
        _diagnostic_for_node_plan(node_plan, graph)
        for node_plan in node_plans
        if not node_plan.implemented
    )
    return ConsoleWriterPlan(
        graph=graph,
        node_plans=node_plans,
        diagnostics=diagnostics,
    )


def _diagnostic_for_node_plan(
    node_plan: ConsoleWriterNodePlan,
    graph: ConsoleGraph,
) -> ConsoleDiagnostic:
    node = graph.node_by_identifier(node_plan.identifier)
    if node_plan.writer_family is None:
        return ConsoleDiagnostic(
            code=PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
            message=(
                f"{node.source_class} is not part of the current Python "
                "Ironbug Console writer registry."
            ),
            source_class=node.source_class,
            identifier=node.identifier,
            path=node.path,
        )
    return ConsoleDiagnostic(
        code=PYCONSOLE_WRITER_NOT_IMPLEMENTED,
        message=(
            f"{node.source_class} is routed to writer family "
            f"{node_plan.writer_family}, but that family is not implemented yet."
        ),
        source_class=node.source_class,
        identifier=node.identifier,
        path=node.path,
    )
