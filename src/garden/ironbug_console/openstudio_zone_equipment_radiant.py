"""Radiant and baseboard ZoneHVAC writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any, Mapping

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
    _temperature_schedule,
)
from garden.ironbug_console.openstudio_coils_basic import (
    _new_heating_water_baseboard,
    _new_heating_water_baseboard_radiant,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_if_present,
    _thermal_zone_name_for_field_reference,
)


def _new_cooling_low_temp_radiant_const_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingLowTempRadiantConstFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingLowTempRadiantConstFlow(
            model,
            _temperature_schedule(openstudio, model, f"{name} High Water", 20.0),
            _temperature_schedule(openstudio, model, f"{name} Low Water", 18.0),
            _temperature_schedule(openstudio, model, f"{name} High Control", 24.0),
            _temperature_schedule(openstudio, model, f"{name} Low Control", 20.0),
        )
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type=coil.iddObjectType().valueDescription(),
        name=name,
    )


def _new_heating_low_temp_radiant_const_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingLowTempRadiantConstFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingLowTempRadiantConstFlow(
            model,
            _temperature_schedule(openstudio, model, f"{name} High Water", 40.0),
            _temperature_schedule(openstudio, model, f"{name} Low Water", 30.0),
            _temperature_schedule(openstudio, model, f"{name} High Control", 22.0),
            _temperature_schedule(openstudio, model, f"{name} Low Control", 18.0),
        )
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type=coil.iddObjectType().valueDescription(),
        name=name,
    )


def _new_cooling_low_temp_radiant_var_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingLowTempRadiantVarFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingLowTempRadiantVarFlow(
            model,
            _temperature_schedule(openstudio, model, f"{name} Control", 26.0),
        )
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type=coil.iddObjectType().valueDescription(),
        name=name,
    )


def _new_heating_low_temp_radiant_var_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingLowTempRadiantVarFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingLowTempRadiantVarFlow(
            model,
            _temperature_schedule(openstudio, model, f"{name} Control", 20.0),
        )
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type=coil.iddObjectType().valueDescription(),
        name=name,
    )


def _write_low_temp_radiant_const_flow(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_node = child_nodes.get(
        "IB_CoilCoolingLowTempRadiantConstFlow",
        _default_low_temp_radiant_child_node(
            node,
            source_class="IB_CoilCoolingLowTempRadiantConstFlow",
            suffix="Cooling Coil",
        ),
    )
    heating_node = child_nodes.get(
        "IB_CoilHeatingLowTempRadiantConstFlow",
        _default_low_temp_radiant_child_node(
            node,
            source_class="IB_CoilHeatingLowTempRadiantConstFlow",
            suffix="Heating Coil",
        ),
    )
    cooling_coil, cooling_summary = _new_cooling_low_temp_radiant_const_flow(
        openstudio,
        model,
        cooling_node,
    )
    heating_coil, heating_summary = _new_heating_low_temp_radiant_const_flow(
        openstudio,
        model,
        heating_node,
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_radiant = model.getZoneHVACLowTempRadiantConstFlowByName(name)
    if optional_radiant.is_initialized():
        radiant = optional_radiant.get()
        radiant.setHeatingCoil(heating_coil)
        radiant.setCoolingCoil(cooling_coil)
    else:
        radiant = openstudio.model.ZoneHVACLowTempRadiantConstFlow(
            model,
            model.alwaysOnDiscreteSchedule(),
            heating_coil,
            cooling_coil,
        )
        radiant.setName(name)
    _apply_generic_openstudio_fields(radiant, node)
    _ensure_low_temp_radiant_pump_power(radiant)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    radiant.addToThermalZone(zone)
    _ensure_low_temp_radiant_internal_source_surfaces(openstudio, model, radiant, zone)
    radiant_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:LowTemperatureRadiant:ConstantFlow",
        name=name,
    )
    return cooling_summary, heating_summary, radiant_summary


def _write_low_temp_radiant_var_flow(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_node = child_nodes.get(
        "IB_CoilCoolingLowTempRadiantVarFlow",
        _default_low_temp_radiant_child_node(
            node,
            source_class="IB_CoilCoolingLowTempRadiantVarFlow",
            suffix="Cooling Coil",
        ),
    )
    heating_node = child_nodes.get(
        "IB_CoilHeatingLowTempRadiantVarFlow",
        _default_low_temp_radiant_child_node(
            node,
            source_class="IB_CoilHeatingLowTempRadiantVarFlow",
            suffix="Heating Coil",
        ),
    )
    cooling_coil, cooling_summary = _new_cooling_low_temp_radiant_var_flow(
        openstudio,
        model,
        cooling_node,
    )
    heating_coil, heating_summary = _new_heating_low_temp_radiant_var_flow(
        openstudio,
        model,
        heating_node,
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_radiant = model.getZoneHVACLowTempRadiantVarFlowByName(name)
    if optional_radiant.is_initialized():
        radiant = optional_radiant.get()
    else:
        radiant = openstudio.model.ZoneHVACLowTempRadiantVarFlow(model)
        radiant.setName(name)
    radiant.setHeatingCoil(heating_coil)
    radiant.setCoolingCoil(cooling_coil)
    _apply_generic_openstudio_fields(radiant, node)
    _ensure_low_temp_radiant_pump_power(radiant)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    radiant.addToThermalZone(zone)
    _ensure_low_temp_radiant_internal_source_surfaces(openstudio, model, radiant, zone)
    radiant_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:LowTemperatureRadiant:VariableFlow",
        name=name,
    )
    return cooling_summary, heating_summary, radiant_summary


def _write_high_temperature_radiant(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_radiant = model.getZoneHVACHighTemperatureRadiantByName(name)
    if optional_radiant.is_initialized():
        radiant = optional_radiant.get()
    else:
        radiant = openstudio.model.ZoneHVACHighTemperatureRadiant(model)
        radiant.setName(name)
    _apply_generic_openstudio_fields(radiant, node)
    heating_schedule = _high_temperature_radiant_schedule(
        openstudio,
        model,
        graph,
        node,
    )
    if heating_schedule is not None:
        radiant.setHeatingSetpointTemperatureSchedule(heating_schedule)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    radiant.addToThermalZone(zone)
    radiant_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:HighTemperatureRadiant",
        name=name,
    )
    return (radiant_summary,)


def _high_temperature_radiant_schedule(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> Any | None:
    schedule_identifier = node.fields.get("HeatingSetpointTemperatureScheduleIdentifier")
    if schedule_identifier is not None:
        schedule_node = graph.node_by_identifier(str(schedule_identifier))
        schedule_name = str(schedule_node.fields.get("Name") or schedule_node.identifier)
        optional_schedule = model.getScheduleRulesetByName(schedule_name)
        if optional_schedule.is_initialized():
            return optional_schedule.get()
    schedule_target = node.fields.get("HeatingSetpointTemperatureSchedule")
    if isinstance(schedule_target, Mapping):
        return _constant_schedule_from_mapping(
            openstudio,
            model,
            schedule_target,
            f"{node.fields.get('Name') or node.identifier} Heating Setpoint",
        )
    return None


def _constant_schedule_from_mapping(
    openstudio: Any,
    model: Any,
    value: Mapping[str, Any],
    default_name: str,
) -> Any:
    name = _source_mapping_name(value, default_name)
    constant_value = value.get("ConstantValue")
    if constant_value is None:
        ib_properties = value.get("IBProperties")
        if isinstance(ib_properties, Mapping):
            constant_value = ib_properties.get("ConstantValue")
    return _temperature_schedule(openstudio, model, name, float(constant_value or 16.0))


def _source_mapping_name(value: Mapping[str, Any], default_name: str) -> str:
    custom_attributes = value.get("CustomAttributes")
    if isinstance(custom_attributes, list):
        for attribute in custom_attributes:
            if not isinstance(attribute, Mapping):
                continue
            field = attribute.get("Field")
            if not isinstance(field, Mapping):
                continue
            if field.get("FullName") == "Name" and attribute.get("Value"):
                return str(attribute["Value"])
    for candidate in (value.get("Name"), value.get("identifier"), value.get("id")):
        if candidate:
            return str(candidate)
    return default_name


def _write_baseboard_convective_water(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    heating_coil, heating_summary = _new_heating_water_baseboard(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingWaterBaseboard"],
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_baseboard = model.getZoneHVACBaseboardConvectiveWaterByName(name)
    if optional_baseboard.is_initialized():
        baseboard = optional_baseboard.get()
        baseboard.setHeatingCoil(heating_coil)
    else:
        baseboard = openstudio.model.ZoneHVACBaseboardConvectiveWater(
            model,
            model.alwaysOnDiscreteSchedule(),
            heating_coil,
        )
        baseboard.setName(name)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    baseboard.addToThermalZone(zone)
    baseboard_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:Baseboard:Convective:Water",
        name=name,
    )
    return heating_summary, baseboard_summary


def _write_baseboard_radiant_convective_water(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    heating_coil, heating_summary = _new_heating_water_baseboard_radiant(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingWaterBaseboardRadiant"],
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_baseboard = model.getZoneHVACBaseboardRadiantConvectiveWaterByName(name)
    if optional_baseboard.is_initialized():
        baseboard = optional_baseboard.get()
        baseboard.setHeatingCoil(heating_coil)
    else:
        baseboard = openstudio.model.ZoneHVACBaseboardRadiantConvectiveWater(model)
        baseboard.setName(name)
        baseboard.setHeatingCoil(heating_coil)
    _set_if_present(baseboard.setFractionRadiant, node, "FractionRadiant")
    _set_if_present(
        baseboard.setFractionofRadiantEnergyIncidentonPeople,
        node,
        "FractionofRadiantEnergyIncidentonPeople",
    )
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    baseboard.addToThermalZone(zone)
    baseboard_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:Baseboard:RadiantConvective:Water",
        name=name,
    )
    return heating_summary, baseboard_summary


def _default_low_temp_radiant_child_node(
    node: ConsoleGraphNode,
    *,
    source_class: str,
    suffix: str,
) -> ConsoleGraphNode:
    name = str(node.fields.get("Name") or node.identifier)
    identifier = f"{node.identifier}_{suffix.lower().replace(' ', '_')}"
    return ConsoleGraphNode(
        identifier=identifier,
        source_class=source_class,
        fields={"Name": f"{name} {suffix}"},
    )


def _ensure_low_temp_radiant_internal_source_surfaces(
    openstudio: Any,
    model: Any,
    radiant: Any,
    zone: Any,
) -> None:
    construction = _low_temp_radiant_internal_source_construction(openstudio, model)
    surface_types = _low_temp_radiant_surface_types(radiant)
    for space in zone.spaces():
        for surface in space.surfaces():
            if surface.surfaceType() not in surface_types:
                continue
            if _surface_has_internal_source_construction(surface):
                continue
            surface.setConstruction(construction)


def _low_temp_radiant_surface_types(radiant: Any) -> set[str]:
    radiant_surface_type = "Floors"
    value = radiant.radiantSurfaceType()
    if value:
        radiant_surface_type = str(value)
    if radiant_surface_type == "Ceilings":
        return {"RoofCeiling"}
    if radiant_surface_type == "CeilingsAndFloors":
        return {"Floor", "RoofCeiling"}
    if radiant_surface_type == "AllSurfaces":
        return {"Floor", "RoofCeiling", "Wall"}
    return {"Floor"}


def _surface_has_internal_source_construction(surface: Any) -> bool:
    optional_construction = surface.construction()
    if not optional_construction.is_initialized():
        return False
    construction = optional_construction.get()
    if not hasattr(construction, "to_ConstructionWithInternalSource"):
        return False
    return construction.to_ConstructionWithInternalSource().is_initialized()


def _low_temp_radiant_internal_source_construction(
    openstudio: Any,
    model: Any,
) -> Any:
    name = "Ironbug Low Temp Radiant Internal Source Construction"
    optional_construction = model.getConstructionWithInternalSourceByName(name)
    if optional_construction.is_initialized():
        return optional_construction.get()
    inside = openstudio.model.StandardOpaqueMaterial(model)
    inside.setName("Ironbug Low Temp Radiant Inside Layer")
    inside.setRoughness("MediumRough")
    inside.setThickness(0.05)
    inside.setConductivity(1.4)
    inside.setDensity(2200.0)
    inside.setSpecificHeat(900.0)
    outside = openstudio.model.StandardOpaqueMaterial(model)
    outside.setName("Ironbug Low Temp Radiant Outside Layer")
    outside.setRoughness("MediumRough")
    outside.setThickness(0.10)
    outside.setConductivity(1.4)
    outside.setDensity(2200.0)
    outside.setSpecificHeat(900.0)
    layers = openstudio.model.MaterialVector()
    layers.append(inside)
    layers.append(outside)
    construction = openstudio.model.ConstructionWithInternalSource(model)
    construction.setName(name)
    construction.setLayers(layers)
    construction.setSourcePresentAfterLayerNumber(1)
    construction.setTemperatureCalculationRequestedAfterLayerNumber(1)
    construction.setTubeSpacing(0.15)
    return construction


def _ensure_low_temp_radiant_pump_power(radiant: Any) -> None:
    if not all(
        hasattr(radiant, method_name)
        for method_name in (
            "ratedFlowRate",
            "ratedPumpHead",
            "motorEfficiency",
            "ratedPowerConsumption",
            "setRatedPowerConsumption",
        )
    ):
        return
    rated_flow = _optional_float(radiant.ratedFlowRate(), 0.002)
    rated_head = _optional_float(radiant.ratedPumpHead(), 179352.0)
    motor_efficiency = max(_optional_float(radiant.motorEfficiency(), 0.9), 0.01)
    rated_power = _optional_float(radiant.ratedPowerConsumption(), 50.0)
    minimum_power = (rated_flow * rated_head / motor_efficiency) * 1.25
    if rated_power <= minimum_power:
        radiant.setRatedPowerConsumption(max(500.0, minimum_power))


def _optional_float(value: Any, default: float) -> float:
    if value is None:
        return default
    if hasattr(value, "is_initialized"):
        if not value.is_initialized():
            return default
        return float(value.get())
    return float(value)
