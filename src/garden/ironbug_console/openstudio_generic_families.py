"""Writer-family routing helpers for generic OpenStudio source classes."""

from __future__ import annotations

from garden.ironbug_console.openstudio_source_classes import (
    GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES as _GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES,
    GENERIC_PLANT_COMPONENT_SOURCE_CLASSES as _GENERIC_PLANT_COMPONENT_SOURCE_CLASSES,
    GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES as _GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES,
    NOOP_CONTAINER_SOURCE_CLASSES as _NOOP_CONTAINER_SOURCE_CLASSES,
    SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES as _SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES,
    SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES as _SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES,
    SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES as _SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES,
)


def _generic_writer_family(source_class: str) -> str:
    if source_class in _NOOP_CONTAINER_SOURCE_CLASSES:
        if source_class in {"IB_HVACSystem", "IB_NoAirLoop"}:
            return "hvac_system"
        if source_class == "IB_ExistAirLoop":
            return "air_loop_components"
        if source_class == "IB_AvailabilityManagerList":
            return "availability_managers"
        if source_class == "IB_EnergyManagementSystem":
            return "ems"
        if source_class == "IB_ZoneEquipmentGroup":
            return "terminal_zone_equipment"
    if (
        source_class in _GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES
        or source_class in _SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES
    ):
        return "air_loop_components"
    if (
        source_class in _GENERIC_PLANT_COMPONENT_SOURCE_CLASSES
        or source_class in _SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES
    ):
        return "plant_components"
    if (
        source_class in _GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES
        or source_class in _SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES
    ):
        return "terminal_zone_equipment"
    if source_class.startswith("IB_AvailabilityManager"):
        return "availability_managers"
    if (
        source_class.startswith("IB_ElectricLoadCenter")
        or source_class.startswith("IB_Generator")
        or source_class.startswith("IB_PhotovoltaicPerformance")
    ):
        return "electric_load_center"
    if source_class.startswith("IB_EnergyManagementSystem"):
        return "ems"
    if source_class.startswith("IB_SolarCollector"):
        return "solar_collectors"
    if source_class.startswith("IB_Water"):
        return "water_systems"
    return "openstudio_objects"
