"""PlantLoop component writer entrypoint for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_cooling_water,
    _new_heating_water,
    _new_heating_water_baseboard,
    _new_heating_water_baseboard_radiant,
)
from garden.ironbug_console.openstudio_coils_beams import (
    _new_cooling_cooled_beam,
    _new_cooling_four_pipe_beam,
    _new_heating_four_pipe_beam,
)
from garden.ironbug_console.openstudio_generic_objects import (
    _new_generic_openstudio_object,
    _new_special_openstudio_object,
)
from garden.ironbug_console.openstudio_plant_chillers_boilers import (
    _new_boiler_hot_water,
    _new_chiller_electric_eir,
)
from garden.ironbug_console.openstudio_plant_district import (
    _new_district_cooling,
    _new_district_heating_water,
)
from garden.ironbug_console.openstudio_plant_heat_exchangers import (
    _new_heat_exchanger_fluid_to_fluid,
)
from garden.ironbug_console.openstudio_plant_heat_rejection import (
    _new_cooling_tower_variable_speed,
)
from garden.ironbug_console.openstudio_plant_pumps import (
    _new_pump_constant_speed,
    _new_pump_variable_speed,
)
from garden.ironbug_console.openstudio_setpoint_managers import (
    _new_setpoint_manager,
)
from garden.ironbug_console.openstudio_solar_collectors import (
    _new_solar_collector_flat_plate_photovoltaic_thermal,
    _new_solar_collector_flat_plate_water,
)
from garden.ironbug_console.openstudio_zone_equipment_radiant import (
    _new_cooling_low_temp_radiant_const_flow,
    _new_cooling_low_temp_radiant_var_flow,
    _new_heating_low_temp_radiant_const_flow,
    _new_heating_low_temp_radiant_var_flow,
)
from garden.ironbug_console.openstudio_source_classes import (
    GENERIC_PLANT_COMPONENT_SOURCE_CLASSES as _GENERIC_PLANT_COMPONENT_SOURCE_CLASSES,
    SETPOINT_MANAGER_SOURCE_CLASSES as _SETPOINT_MANAGER_SOURCE_CLASSES,
    SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES as _SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_water_systems import (
    _new_water_use_connections,
    _new_water_use_equipment,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext


def _new_plant_component(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
    graph: ConsoleGraph | None = None,
    context: OpenStudioWriterContext | None = None,
) -> tuple[Any, OpenStudioWrittenObject]:
    if node.source_class == "IB_ChillerElectricEIR":
        return _new_chiller_electric_eir(openstudio, model, node)
    if node.source_class == "IB_CoolingTowerVariableSpeed":
        return _new_cooling_tower_variable_speed(openstudio, model, node)
    if node.source_class == "IB_BoilerHotWater":
        return _new_boiler_hot_water(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingWater":
        return _new_cooling_water(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingWater":
        return _new_heating_water(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingWaterBaseboard":
        return _new_heating_water_baseboard(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingWaterBaseboardRadiant":
        return _new_heating_water_baseboard_radiant(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingFourPipeBeam":
        return _new_cooling_four_pipe_beam(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingCooledBeam":
        return _new_cooling_cooled_beam(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingFourPipeBeam":
        return _new_heating_four_pipe_beam(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingLowTempRadiantConstFlow":
        return _new_cooling_low_temp_radiant_const_flow(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingLowTempRadiantConstFlow":
        return _new_heating_low_temp_radiant_const_flow(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingLowTempRadiantVarFlow":
        return _new_cooling_low_temp_radiant_var_flow(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingLowTempRadiantVarFlow":
        return _new_heating_low_temp_radiant_var_flow(openstudio, model, node)
    if node.source_class == "IB_PumpConstantSpeed":
        return _new_pump_constant_speed(openstudio, model, node)
    if node.source_class == "IB_PumpVariableSpeed":
        return _new_pump_variable_speed(openstudio, model, node)
    if node.source_class == "IB_DistrictCooling":
        return _new_district_cooling(openstudio, model, node)
    if node.source_class == "IB_DistrictHeatingWater":
        return _new_district_heating_water(openstudio, model, node)
    if node.source_class == "IB_HeatExchangerFluidToFluid":
        return _new_heat_exchanger_fluid_to_fluid(openstudio, model, node)
    if node.source_class == "IB_SolarCollectorFlatPlateWater":
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        return _new_solar_collector_flat_plate_water(openstudio, model, graph, node)
    if node.source_class == "IB_SolarCollectorFlatPlatePhotovoltaicThermal":
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        return _new_solar_collector_flat_plate_photovoltaic_thermal(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_WaterUseConnections":
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        return _new_water_use_connections(openstudio, model, graph, node)
    if node.source_class == "IB_WaterUseEquipment":
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        return _new_water_use_equipment(openstudio, model, graph, node)
    if node.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        return _new_setpoint_manager(openstudio, model, graph, node, context)
    if node.source_class in _GENERIC_PLANT_COMPONENT_SOURCE_CLASSES:
        return _new_generic_openstudio_object(openstudio, model, node)
    if node.source_class in _SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES:
        return _new_special_openstudio_object(openstudio, model, node)
    raise ValueError(f"Unsupported PlantLoop component: {node.source_class}")
