"""Decode state for Ironbug Console graph decoding."""

from __future__ import annotations

from dataclasses import dataclass, field

from ironbug.console_ir import ConsoleGraphNode


@dataclass
class _DecodeState:
    nodes: list[ConsoleGraphNode] = field(default_factory=list)
    fallback_index: int = 0

    def next_identifier(self, source_class: str) -> str:
        self.fallback_index += 1
        return f"{source_class}_{self.fallback_index}"

    def add_node(self, node: ConsoleGraphNode) -> None:
        for index, existing in enumerate(self.nodes):
            if existing.identifier != node.identifier:
                continue
            if existing.source_class != node.source_class:
                raise ValueError(
                    "Duplicate Python Console graph node identifier with "
                    f"different source classes: {node.identifier}"
                )
            merged_children = tuple(
                [
                    *existing.children,
                    *(
                        child
                        for child in node.children
                        if child not in existing.children
                    ),
                ]
            )
            self.nodes[index] = ConsoleGraphNode(
                identifier=existing.identifier,
                source_class=existing.source_class,
                path=existing.path,
                fields={**node.fields, **existing.fields},
                children=merged_children,
            )
            return
        self.nodes.append(node)
