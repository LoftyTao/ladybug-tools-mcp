"""Water-system writers for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


def _new_water_use_equipment(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    definition = _water_use_equipment_definition(openstudio, model, graph, node)
    optional_equipment = model.getWaterUseEquipmentByName(name)
    if optional_equipment.is_initialized():
        equipment = optional_equipment.get()
        equipment.setWaterUseEquipmentDefinition(definition)
    else:
        equipment = openstudio.model.WaterUseEquipment(definition)
    equipment.setName(name)
    _apply_generic_openstudio_fields(equipment, node)
    return equipment, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="water_systems",
        openstudio_type=equipment.iddObjectType().valueDescription(),
        name=name,
    )


def _new_water_use_connections(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    connections, summary = _new_generic_openstudio_object(openstudio, model, node)
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_WaterUseEquipment":
            continue
        equipment, _equipment_summary = _new_water_use_equipment(
            openstudio,
            model,
            graph,
            child,
        )
        if equipment not in connections.waterUseEquipment():
            connections.addWaterUseEquipment(equipment)
    return connections, summary


def _water_use_equipment_definition(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> Any:
    child = _first_definition_child(graph, node)
    name = str(
        (child.fields.get("Name") if child is not None else None)
        or f"{node.fields.get('Name') or node.identifier} Definition"
    )
    optional_definition = model.getWaterUseEquipmentDefinitionByName(name)
    if optional_definition.is_initialized():
        definition = optional_definition.get()
    else:
        definition = openstudio.model.WaterUseEquipmentDefinition(model)
    definition.setName(name)
    if child is not None:
        _apply_generic_openstudio_fields(definition, child)
    return definition


def _first_definition_child(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> ConsoleGraphNode | None:
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_WaterUseEquipmentDefinition":
            return child
    return None
