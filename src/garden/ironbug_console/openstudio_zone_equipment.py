"""Zone equipment writer entrypoints for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from garden.ironbug_console.openstudio_zone_equipment_fan_coils import (
    _write_four_pipe_fan_coil,
)
from garden.ironbug_console.openstudio_zone_equipment_packaged import (
    _write_ptac,
    _write_pthp,
    _write_water_to_air_heat_pump,
)
from garden.ironbug_console.openstudio_zone_equipment_radiant import (
    _write_baseboard_convective_water,
    _write_baseboard_radiant_convective_water,
    _write_high_temperature_radiant,
    _write_low_temp_radiant_const_flow,
    _write_low_temp_radiant_var_flow,
)
from garden.ironbug_console.openstudio_zone_equipment_unit_heaters import (
    _write_unit_heater,
)
from garden.ironbug_console.openstudio_zone_equipment_unit_ventilators import (
    _write_unit_ventilator_cooling_heating,
    _write_unit_ventilator_cooling_only,
    _write_unit_ventilator_heating_only,
)

_ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES = frozenset(
    {
        "IB_ZoneHVACPackagedTerminalAirConditioner",
        "IB_ZoneHVACPackagedTerminalHeatPump",
        "IB_ZoneHVACFourPipeFanCoil",
        "IB_ZoneHVACWaterToAirHeatPump",
        "IB_ZoneHVACBaseboardRadiantConvectiveWater",
        "IB_ZoneHVACUnitHeater",
        "IB_ZoneHVACUnitVentilator_CoolingHeating",
        "IB_ZoneHVACUnitVentilator_CoolingOnly",
        "IB_ZoneHVACUnitVentilator_HeatingOnly",
    }
)


def _write_zone_hvac_equipment(openstudio, model, graph, node):
    if node.source_class == "IB_ZoneHVACPackagedTerminalAirConditioner":
        return _write_ptac(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACPackagedTerminalHeatPump":
        return _write_pthp(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACUnitHeater":
        return _write_unit_heater(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACFourPipeFanCoil":
        return _write_four_pipe_fan_coil(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACWaterToAirHeatPump":
        return _write_water_to_air_heat_pump(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACBaseboardRadiantConvectiveWater":
        return _write_baseboard_radiant_convective_water(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_ZoneHVACUnitVentilator_CoolingHeating":
        return _write_unit_ventilator_cooling_heating(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACUnitVentilator_CoolingOnly":
        return _write_unit_ventilator_cooling_only(openstudio, model, graph, node)
    if node.source_class == "IB_ZoneHVACUnitVentilator_HeatingOnly":
        return _write_unit_ventilator_heating_only(openstudio, model, graph, node)
    raise ValueError(f"Unsupported ZoneHVAC equipment: {node.source_class}")


def _zone_hvac_component_by_node(model, node):
    name = str(node.fields.get("Name") or node.identifier)
    if node.source_class == "IB_ZoneHVACPackagedTerminalAirConditioner":
        optional = model.getZoneHVACPackagedTerminalAirConditionerByName(name)
    elif node.source_class == "IB_ZoneHVACPackagedTerminalHeatPump":
        optional = model.getZoneHVACPackagedTerminalHeatPumpByName(name)
    elif node.source_class == "IB_ZoneHVACFourPipeFanCoil":
        optional = model.getZoneHVACFourPipeFanCoilByName(name)
    elif node.source_class == "IB_ZoneHVACWaterToAirHeatPump":
        optional = model.getZoneHVACWaterToAirHeatPumpByName(name)
    elif node.source_class == "IB_ZoneHVACBaseboardRadiantConvectiveWater":
        optional = model.getZoneHVACBaseboardRadiantConvectiveWaterByName(name)
    elif node.source_class == "IB_ZoneHVACUnitHeater":
        optional = model.getZoneHVACUnitHeaterByName(name)
    elif node.source_class in {
        "IB_ZoneHVACUnitVentilator_CoolingHeating",
        "IB_ZoneHVACUnitVentilator_CoolingOnly",
        "IB_ZoneHVACUnitVentilator_HeatingOnly",
    }:
        optional = model.getZoneHVACUnitVentilatorByName(name)
    else:
        return None
    if optional.is_initialized():
        return optional.get()
    return None

__all__ = (
    "_ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES",
    "_write_baseboard_radiant_convective_water",
    "_write_four_pipe_fan_coil",
    "_write_high_temperature_radiant",
    "_write_low_temp_radiant_const_flow",
    "_write_low_temp_radiant_var_flow",
    "_write_ptac",
    "_write_pthp",
    "_write_water_to_air_heat_pump",
    "_write_unit_heater",
    "_write_unit_ventilator_cooling_heating",
    "_write_unit_ventilator_cooling_only",
    "_write_unit_ventilator_heating_only",
    "_write_zone_hvac_equipment",
    "_zone_hvac_component_by_node",
)
