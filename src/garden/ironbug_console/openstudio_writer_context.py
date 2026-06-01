"""Shared state for one Python Console OpenStudio write pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenStudioWriterContext:
    """Track OpenStudio object references that C# records with OpsIDMapper."""

    node_probes: dict[str, Any] = field(default_factory=dict)
    _pending_reference_nodes: list[tuple[Any, str, str]] = field(
        default_factory=list
    )

    def register_node_probe(self, identifier: str, node: Any) -> None:
        self.node_probes[str(identifier)] = node

    def bind_reference_node(
        self,
        manager: Any,
        *,
        probe_identifier: str | None,
        owner: str,
    ) -> None:
        if not probe_identifier:
            return
        probe_id = str(probe_identifier)
        node = self.node_probes.get(probe_id)
        if node is None:
            self._pending_reference_nodes.append((manager, probe_id, owner))
            return
        if not manager.setReferenceNode(node):
            raise ValueError(f"Failed to bind node probe {probe_id} for {owner}.")

    def resolve_pending_reference_nodes(self) -> None:
        unresolved: list[str] = []
        for manager, probe_id, owner in self._pending_reference_nodes:
            node = self.node_probes.get(probe_id)
            if node is None:
                unresolved.append(f"{owner}: {probe_id}")
                continue
            if not manager.setReferenceNode(node):
                unresolved.append(f"{owner}: {probe_id}")
        self._pending_reference_nodes = []
        if unresolved:
            raise ValueError(
                "Failed to bind node probe reference(s): "
                + ", ".join(unresolved)
            )
