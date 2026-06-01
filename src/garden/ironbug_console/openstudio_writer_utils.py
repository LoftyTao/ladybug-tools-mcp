"""Shared helpers for Python Ironbug OpenStudio writer modules."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)


def _append_written(
    written_objects: list[OpenStudioWrittenObject],
    new_objects: tuple[OpenStudioWrittenObject, ...],
) -> None:
    seen_identifiers = {item.identifier for item in written_objects}
    for written_object in new_objects:
        if written_object.identifier in seen_identifiers:
            continue
        written_objects.append(written_object)
        seen_identifiers.add(written_object.identifier)


def _set_if_present(
    setter: Any,
    node: ConsoleGraphNode,
    field_name: str,
    *,
    cast: Any = float,
) -> None:
    value = node.fields.get(field_name)
    if value is not None:
        setter(cast(value))


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def _set_autosizable_if_present(
    setter: Any,
    autosize: Any,
    node: ConsoleGraphNode,
    field_name: str,
) -> None:
    value = node.fields.get(field_name)
    if value is None:
        return
    if _is_autosize(value):
        autosize()
        return
    setter(float(value))


def _set_int_autosizable_if_present(
    setter: Any,
    autosize: Any,
    node: ConsoleGraphNode,
    field_name: str,
) -> None:
    value = node.fields.get(field_name)
    if value is None:
        return
    if _is_autosize(value):
        autosize()
        return
    setter(int(value))


def _is_autosize(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() == "autosize"
    if isinstance(value, int | float):
        return float(value) == -9999.0
    return False


def _source_classes_for_identifiers(
    graph: ConsoleGraph,
    identifiers: tuple[Any, ...],
) -> set[str]:
    source_classes: set[str] = set()
    for identifier in identifiers:
        node = graph.node_by_identifier(str(identifier))
        source_classes.add(node.source_class)
        source_classes.update(_source_classes_for_identifiers(graph, node.children))
    return source_classes


def _thermal_zone_name_for_field_reference(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> str:
    zone_identifier = str(node.fields["ThermalZoneIdentifier"])
    zone_node = graph.node_by_identifier(zone_identifier)
    return str(zone_node.fields.get("Name") or zone_node.identifier)


def _referenced_node_name(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    *field_names: str,
) -> str:
    for field_name in field_names:
        if field_name in node.fields:
            referenced = graph.node_by_identifier(str(node.fields[field_name]))
            return str(referenced.fields.get("Name") or referenced.identifier)
    raise KeyError(
        f"{node.source_class} requires one of {', '.join(field_names)}."
    )


def _child_nodes_by_source_class(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> dict[str, ConsoleGraphNode]:
    child_nodes = [
        graph.node_by_identifier(identifier)
        for identifier in node.children
    ]
    return {child.source_class: child for child in child_nodes}


def _has_node(graph: ConsoleGraph, identifier: str) -> bool:
    try:
        graph.node_by_identifier(identifier)
    except KeyError:
        return False
    return True
