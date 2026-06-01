"""Basic OpenStudio object writers for Python Ironbug source nodes."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)


def _write_thermal_zone(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    optional_zone = model.getThermalZoneByName(name)
    if optional_zone.is_initialized():
        zone = optional_zone.get()
    else:
        zone = openstudio.model.ThermalZone(model)
        zone.setName(name)
    multiplier = node.fields.get("Multiplier")
    if multiplier is not None:
        zone.setMultiplier(int(multiplier))
    if node.fields.get("UseIdealAirLoads") is True:
        ideal_loads = openstudio.model.ZoneHVACIdealLoadsAirSystem(model)
        ideal_loads.setName(f"{name} Ideal Loads")
        ideal_loads.addToThermalZone(zone)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="thermal_zone",
        openstudio_type="OS:ThermalZone",
        name=name,
    )


def _write_output_variable(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    variable_name = str(
        node.fields.get("VariableName")
        or node.fields.get("variable_name")
        or node.identifier
    )
    reporting_frequency = str(
        node.fields.get("ReportingFrequency")
        or node.fields.get("reporting_frequency")
        or "Hourly"
    )
    output_variable = openstudio.model.OutputVariable(variable_name, model)
    output_variable.setReportingFrequency(reporting_frequency)
    key_value = node.fields.get("KeyValue") or node.fields.get("key_value")
    if key_value:
        output_variable.setKeyValue(str(key_value))
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="output_requests",
        openstudio_type="OS:Output:Variable",
        name=variable_name,
    )
