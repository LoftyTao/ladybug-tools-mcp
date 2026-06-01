"""Writer wrappers for generic and special OpenStudio object factories."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_families import _generic_writer_family
from garden.ironbug_console.openstudio_special_objects import (
    _new_special_openstudio_object,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


def _write_generic_openstudio_object(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    _component, summary = _new_generic_openstudio_object(openstudio, model, node)
    return summary


def _write_ems_program_calling_manager(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    manager, summary = _new_generic_openstudio_object(openstudio, model, node)
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_EnergyManagementSystemProgram":
            continue
        program_name = str(child.fields.get("Name") or child.identifier)
        program = model.getEnergyManagementSystemProgramByName(program_name)
        if program.is_initialized():
            manager.addProgram(program.get())
    return summary


def _write_special_openstudio_object(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    _component, summary = _new_special_openstudio_object(openstudio, model, node)
    return summary


def _write_noop_source_object(node: ConsoleGraphNode) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family=_generic_writer_family(node.source_class),
        openstudio_type="Ironbug:Container",
        name=name,
    )


def _write_generic_zone_equipment(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    equipment, summary = _new_generic_openstudio_object(openstudio, model, node)
    zone_identifier = node.fields.get("ThermalZoneIdentifier")
    if zone_identifier is not None:
        zone_node = graph.node_by_identifier(str(zone_identifier))
        zone_name = str(zone_node.fields.get("Name") or zone_node.identifier)
        optional_zone = model.getThermalZoneByName(zone_name)
        if optional_zone.is_initialized() and hasattr(equipment, "addToThermalZone"):
            equipment.addToThermalZone(optional_zone.get())
    return (summary,)


def _write_special_zone_equipment(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    equipment, summary = _new_special_openstudio_object(openstudio, model, node)
    zone_identifier = node.fields.get("ThermalZoneIdentifier")
    if zone_identifier is not None:
        zone_node = graph.node_by_identifier(str(zone_identifier))
        zone_name = str(zone_node.fields.get("Name") or zone_node.identifier)
        optional_zone = model.getThermalZoneByName(zone_name)
        if optional_zone.is_initialized() and hasattr(equipment, "addToThermalZone"):
            equipment.addToThermalZone(optional_zone.get())
    return (summary,)
