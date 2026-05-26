"""EnergyPlus Plant Application Guide coverage metadata for Ironbug."""

from __future__ import annotations

from typing import Any


ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_2_URL = (
    "https://bigladdersoftware.com/epx/docs/26-1/plant-application-guide/"
    "example-02-thermal-energy-storage.html"
)
ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_3_URL = (
    "https://bigladdersoftware.com/epx/docs/26-1/plant-application-guide/"
    "example-system-3-primary-secondary-pumping.html"
)

PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_STATUSES = {
    "source-backed",
    "missing",
    "blocked-translator",
}


def _source_metadata(class_names: list[str]) -> list[dict[str, str]]:
    metadata: list[dict[str, str]] = []
    import ironbug.hvac as hvac

    for class_name in class_names:
        cls = getattr(hvac, class_name)
        metadata.append(
            {
                "ironbug_class": class_name,
                "source_path": cls.SOURCE_PATH,
                "source_namespace": cls.SOURCE_NAMESPACE,
            }
        )
    return metadata


def _coverage_item(
    *,
    role: str,
    status: str,
    energyplus_objects: list[str],
    ironbug_classes: list[str] | None = None,
    note: str,
    translator_note: str | None = None,
) -> dict[str, Any]:
    if status not in PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_STATUSES:
        raise ValueError(f"Unsupported coverage status: {status}")
    class_names = ironbug_classes or []
    item: dict[str, Any] = {
        "role": role,
        "status": status,
        "energyplus_objects": energyplus_objects,
        "note": note,
    }
    if class_names:
        item["ironbug_classes"] = class_names
        item["source_metadata"] = _source_metadata(class_names)
    if translator_note is not None:
        item["translator_note"] = translator_note
    return item


def _missing_coverage_item(
    *,
    role: str,
    energyplus_objects: list[str],
    missing_source_class: str,
    note: str,
    not_equivalent_classes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "status": "missing",
        "energyplus_objects": energyplus_objects,
        "missing_source_class": missing_source_class,
        "not_equivalent_classes": not_equivalent_classes or [],
        "note": note,
    }


PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_MATRIX: dict[str, Any] = {
    "example_2": {
        "energyplus_reference": {
            "guide": "EnergyPlus Plant Application Guide",
            "version": "26.1",
            "example": "Example System 2: Thermal Energy Storage",
            "url": ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_2_URL,
        },
        "metadata_only": True,
        "simulation_claim": False,
        "overall_status": "missing",
        "blocking_gap": "stratified_thermal_energy_storage_source_class",
        "coverage": {
            "thermal_storage": _missing_coverage_item(
                role="stratified_thermal_energy_storage_tank",
                energyplus_objects=["ThermalStorage:ChilledWater:Stratified"],
                missing_source_class="IB_ThermalStorageChilledWaterStratified",
                not_equivalent_classes=["IB_WaterHeaterMixed"],
                note=(
                    "No source-backed Ironbug class for the stratified chilled "
                    "water TES object is present in ironbug.hvac. "
                    "IB_WaterHeaterMixed is a mixed domestic/service water tank "
                    "mirror and is not equivalent."
                ),
            ),
            "chiller": _coverage_item(
                role="water_cooled_chiller",
                status="source-backed",
                energyplus_objects=["Chiller:Electric:EIR"],
                ironbug_classes=["IB_ChillerElectricEIR"],
                note="Chiller source mirror exists for the cooling plant equipment.",
            ),
            "condenser_loop": _coverage_item(
                role="condenser_loop_and_tower",
                status="source-backed",
                energyplus_objects=[
                    "PlantLoop",
                    "Pump:ConstantSpeed",
                    "CoolingTower:VariableSpeed",
                ],
                ironbug_classes=[
                    "IB_PlantLoop",
                    "IB_PumpConstantSpeed",
                    "IB_CoolingTowerVariableSpeed",
                ],
                note="Loop, pump, and tower source mirrors exist.",
            ),
            "boiler_heating_loop": _coverage_item(
                role="boiler_and_heating_loop",
                status="source-backed",
                energyplus_objects=[
                    "PlantLoop",
                    "Pump:ConstantSpeed",
                    "Boiler:HotWater",
                ],
                ironbug_classes=[
                    "IB_PlantLoop",
                    "IB_PumpConstantSpeed",
                    "IB_BoilerHotWater",
                ],
                note="Heating loop, pump, and hot-water boiler source mirrors exist.",
            ),
            "cooling_heating_reheat_coils": _coverage_item(
                role="water_coils_and_reheat_coil",
                status="source-backed",
                energyplus_objects=[
                    "Coil:Cooling:Water",
                    "Coil:Heating:Water",
                ],
                ironbug_classes=["IB_CoilCoolingWater", "IB_CoilHeatingWater"],
                note=(
                    "Cooling, heating, and water reheat coil object mirrors are "
                    "available as water coil classes."
                ),
            ),
            "operation_schemes": _coverage_item(
                role="cooling_and_heating_load_operation_schemes",
                status="blocked-translator",
                energyplus_objects=[
                    "PlantEquipmentOperation:CoolingLoad",
                    "PlantEquipmentOperation:HeatingLoad",
                ],
                ironbug_classes=[
                    "IB_PlantEquipmentOperationCoolingLoad",
                    "IB_PlantEquipmentOperationHeatingLoad",
                ],
                note="Operation scheme source mirrors exist.",
                translator_note=(
                    "Example 2 remains metadata-only until the complete "
                    "TES topology has a translator/runtime probe."
                ),
            ),
            "setpoint_managers": _coverage_item(
                role="plant_loop_setpoint_managers",
                status="source-backed",
                energyplus_objects=["SetpointManager:Scheduled"],
                ironbug_classes=["IB_SetpointManagerScheduled"],
                note="Scheduled setpoint manager source mirror exists.",
            ),
        },
    },
    "example_3": {
        "energyplus_reference": {
            "guide": "EnergyPlus Plant Application Guide",
            "version": "26.1",
            "example": "Example System 3: Primary/Secondary Pumping",
            "url": ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_3_URL,
        },
        "metadata_only": True,
        "simulation_claim": False,
        "overall_status": "source-backed-plant-core",
        "blocking_gap": "exact_example_3_source_class_gaps",
        "plant_core_runtime_probe_ready": True,
        "exact_fidelity_blockers": [
            "IB_ChillerElectric",
            "IB_ChillerConstantCOP",
            "IB_CoilCoolingWaterDetailedGeometry",
        ],
        "not_equivalent_substitutions": [
            "IB_ChillerElectricEIR",
            "IB_CoilCoolingWater",
        ],
        "simulation_scope": (
            "Ironbug can build a source-backed primary/secondary plant-core "
            "probe for Example 3 using the mirrored loops, pumps, heat "
            "exchanger, district cooling/heating, condenser tower, scheduled "
            "setpoints, and operation schemes. Exact official-IDF fidelity is "
            "not claimed because the official case also uses Chiller:Electric, "
            "Chiller:ConstantCOP, and Coil:Cooling:Water:DetailedGeometry "
            "objects that do not currently have one-to-one Ironbug source "
            "mirror classes."
        ),
        "coverage": {
            "primary_chilled_water_loop": _coverage_item(
                role="primary_chilled_water_loop",
                status="source-backed",
                energyplus_objects=["PlantLoop"],
                ironbug_classes=["IB_PlantLoop"],
                note="Primary chilled water plant loop source mirror exists.",
            ),
            "secondary_chilled_water_loop": _coverage_item(
                role="secondary_chilled_water_loop",
                status="source-backed",
                energyplus_objects=["PlantLoop"],
                ironbug_classes=["IB_PlantLoop"],
                note="Secondary chilled water plant loop source mirror exists.",
            ),
            "constant_speed_pump": _coverage_item(
                role="primary_constant_speed_pump",
                status="source-backed",
                energyplus_objects=["Pump:ConstantSpeed"],
                ironbug_classes=["IB_PumpConstantSpeed"],
                note="Constant speed pump source mirror exists.",
            ),
            "variable_speed_pump": _coverage_item(
                role="secondary_variable_speed_pump",
                status="source-backed",
                energyplus_objects=["Pump:VariableSpeed"],
                ironbug_classes=["IB_PumpVariableSpeed"],
                note="Variable speed pump source mirror exists.",
            ),
            "electric_eir_chiller_available": _coverage_item(
                role="electric_eir_chiller_available_for_other_chiller_cases",
                status="source-backed",
                energyplus_objects=["Chiller:Electric:EIR"],
                ironbug_classes=["IB_ChillerElectricEIR"],
                note=(
                    "Electric EIR chiller source mirror exists, but the official "
                    "Example 3 IDF uses Chiller:Electric and Chiller:ConstantCOP. "
                    "The EIR object must not be treated as exact source fidelity "
                    "for those official objects."
                ),
            ),
            "simple_electric_chiller_exact": _missing_coverage_item(
                role="official_simple_electric_chiller",
                energyplus_objects=["Chiller:Electric"],
                missing_source_class="IB_ChillerElectric",
                not_equivalent_classes=["IB_ChillerElectricEIR"],
                note=(
                    "The official Example 3 primary loop includes Chiller:Electric. "
                    "Current Ironbug source mirror exposes IB_ChillerElectricEIR, "
                    "not a one-to-one IB_ChillerElectric class."
                ),
            ),
            "constant_cop_chiller_exact": _missing_coverage_item(
                role="official_constant_cop_chiller",
                energyplus_objects=["Chiller:ConstantCOP"],
                missing_source_class="IB_ChillerConstantCOP",
                not_equivalent_classes=["IB_ChillerElectricEIR"],
                note=(
                    "The official Example 3 primary loop includes "
                    "Chiller:ConstantCOP. Current Ironbug source mirror has no "
                    "one-to-one class for that object."
                ),
            ),
            "purchased_cooling": _coverage_item(
                role="purchased_cooling",
                status="source-backed",
                energyplus_objects=["DistrictCooling"],
                ironbug_classes=["IB_DistrictCooling"],
                note="Purchased cooling is represented by the DistrictCooling mirror.",
            ),
            "fluid_to_fluid_heat_exchanger": _coverage_item(
                role="plate_heat_exchanger",
                status="source-backed",
                energyplus_objects=["HeatExchanger:FluidToFluid"],
                ironbug_classes=["IB_HeatExchangerFluidToFluid"],
                note="Fluid-to-fluid heat exchanger source mirror exists.",
            ),
            "condenser_loop_tower": _coverage_item(
                role="condenser_loop_and_tower",
                status="source-backed",
                energyplus_objects=[
                    "PlantLoop",
                    "Pump:VariableSpeed",
                    "CoolingTower:SingleSpeed",
                ],
                ironbug_classes=[
                    "IB_PlantLoop",
                    "IB_PumpVariableSpeed",
                    "IB_CoolingTowerSingleSpeed",
                ],
                note="Condenser loop, pump, and tower source mirrors exist.",
            ),
            "purchased_heating": _coverage_item(
                role="purchased_heating",
                status="source-backed",
                energyplus_objects=["DistrictHeating:Water"],
                ironbug_classes=["IB_DistrictHeatingWater"],
                note=(
                    "Purchased heating is represented by the DistrictHeating "
                    "water mirror."
                ),
            ),
            "detailed_geometry_cooling_coil_exact": _missing_coverage_item(
                role="official_air_loop_detailed_geometry_cooling_coil",
                energyplus_objects=["Coil:Cooling:Water:DetailedGeometry"],
                missing_source_class="IB_CoilCoolingWaterDetailedGeometry",
                not_equivalent_classes=["IB_CoilCoolingWater"],
                note=(
                    "The official Example 3 air loop uses "
                    "Coil:Cooling:Water:DetailedGeometry. Current Ironbug source "
                    "mirror exposes the generic IB_CoilCoolingWater class, not "
                    "the detailed-geometry object."
                ),
            ),
            "air_loop_and_reheat_terminals": _coverage_item(
                role="air_loop_outdoor_air_system_and_reheat_terminals",
                status="source-backed",
                energyplus_objects=[
                    "AirLoopHVAC",
                    "AirLoopHVAC:OutdoorAirSystem",
                    "Controller:OutdoorAir",
                    "Controller:WaterCoil",
                    "Fan:ConstantVolume",
                    "AirTerminal:SingleDuct:ConstantVolume:Reheat",
                ],
                ironbug_classes=[
                    "IB_AirLoopHVAC",
                    "IB_OutdoorAirSystem",
                    "IB_ControllerOutdoorAir",
                    "IB_ControllerWaterCoil",
                    "IB_FanConstantVolume",
                    "IB_AirTerminalSingleDuctConstantVolumeReheat",
                ],
                note=(
                    "Air loop, outdoor-air system/controller, fan, water-coil "
                    "controller, and constant-volume reheat terminal mirrors are "
                    "available. The exact official cooling coil remains a missing "
                    "source class."
                ),
            ),
            "reheat_coils": _coverage_item(
                role="water_reheat_coils",
                status="source-backed",
                energyplus_objects=["Coil:Heating:Water"],
                ironbug_classes=["IB_CoilHeatingWater"],
                note="Water heating coil source mirror exists for reheat coils.",
            ),
        },
    },
}


ENERGYPLUS_HVAC_SYSTEM_ROADMAP: list[dict[str, Any]] = [
    {
        "id": "plant_app_guide_example_1_chiller_condenser",
        "name": "Plant Application Guide Example 1: chiller and condenser loops",
        "status": "garden-simulated",
        "energyplus_reference": [
            "EnergyPlus Plant Application Guide Example System 1",
            "Chiller:Electric:EIR",
            "CoolingTower:VariableSpeed",
        ],
        "ironbug_classes": [
            "IB_PlantLoop",
            "IB_PumpConstantSpeed",
            "IB_ChillerElectricEIR",
            "IB_CoolingTowerVariableSpeed",
            "IB_LoadProfilePlant",
            "IB_PlantEquipmentOperationCoolingLoad",
            "IB_SetpointManagerScheduled",
            "IB_SizingPlant",
        ],
        "missing_exact_classes": [],
        "next_work": "Retain as regression baseline for Garden energy simulation.",
    },
    {
        "id": "plant_app_guide_example_3_primary_secondary_plant_core",
        "name": "Plant Application Guide Example 3: primary/secondary plant core",
        "status": "next-implementation",
        "energyplus_reference": [
            "EnergyPlus Plant Application Guide Example System 3",
            "Primary/Secondary Pumping",
            "HeatExchanger:FluidToFluid",
            "DistrictCooling",
            "CoolingTower:SingleSpeed",
        ],
        "ironbug_classes": [
            "IB_PlantLoop",
            "IB_PumpConstantSpeed",
            "IB_PumpVariableSpeed",
            "IB_DistrictCooling",
            "IB_HeatExchangerFluidToFluid",
            "IB_CoolingTowerSingleSpeed",
            "IB_LoadProfilePlant",
            "IB_PlantEquipmentOperationCoolingLoad",
            "IB_SetpointManagerScheduled",
            "IB_SetpointManagerFollowOutdoorAirTemperature",
            "IB_SizingPlant",
        ],
        "missing_exact_classes": [
            "IB_ChillerElectric",
            "IB_ChillerConstantCOP",
            "IB_CoilCoolingWaterDetailedGeometry",
        ],
        "next_work": (
            "Implement a plant-only source-backed slice first; do not claim "
            "official full Example 3 fidelity until the missing exact classes exist."
        ),
    },
    {
        "id": "district_cooling_heating_plant_loops",
        "name": "District cooling and district heating plant loops",
        "status": "source-backed-needs-probe",
        "energyplus_reference": [
            "DistrictCooling",
            "DistrictHeating:Water",
            "DistrictHeating:Steam",
        ],
        "ironbug_classes": [
            "IB_PlantLoop",
            "IB_DistrictCooling",
            "IB_DistrictHeatingWater",
            "IB_DistrictHeatingSteam",
            "IB_PumpVariableSpeed",
            "IB_SetpointManagerScheduled",
        ],
        "missing_exact_classes": [],
        "next_work": "Build low-risk cooling/heating purchased-energy Garden probes.",
    },
    {
        "id": "boiler_hot_water_reheat_loop",
        "name": "Boiler hot-water loop with water reheat coils",
        "status": "source-backed-needs-probe",
        "energyplus_reference": [
            "Boiler:HotWater",
            "Coil:Heating:Water",
            "PlantEquipmentOperation:HeatingLoad",
        ],
        "ironbug_classes": [
            "IB_PlantLoop",
            "IB_BoilerHotWater",
            "IB_CoilHeatingWater",
            "IB_PumpConstantSpeed",
            "IB_PlantEquipmentOperationHeatingLoad",
            "IB_SetpointManagerScheduled",
            "IB_SizingPlant",
        ],
        "missing_exact_classes": [],
        "next_work": "Extend Garden runtime repair to heating-load operation schemes.",
    },
    {
        "id": "cav_reheat_air_loop",
        "name": "Constant-volume air loop with water reheat terminals",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "AirLoopHVAC",
            "Fan:ConstantVolume",
            "AirTerminal:SingleDuct:ConstantVolume:Reheat",
            "Coil:Heating:Water",
        ],
        "ironbug_classes": [
            "IB_AirLoopHVAC",
            "IB_FanConstantVolume",
            "IB_OutdoorAirSystem",
            "IB_ControllerOutdoorAir",
            "IB_ControllerWaterCoil",
            "IB_AirTerminalSingleDuctConstantVolumeReheat",
            "IB_CoilHeatingWater",
        ],
        "missing_exact_classes": [],
        "next_work": "Probe air-loop DetailedHVAC assignment after plant-core loops.",
    },
    {
        "id": "vav_reheat_air_loop",
        "name": "Variable-air-volume air loop with reheat terminals",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "AirTerminal:SingleDuct:VAV:Reheat",
            "Fan:VariableVolume",
            "Coil:Cooling:Water",
            "Coil:Heating:Water",
        ],
        "ironbug_classes": [
            "IB_AirLoopHVAC",
            "IB_FanVariableVolume",
            "IB_CoilCoolingWater",
            "IB_CoilHeatingWater",
            "IB_AirTerminalSingleDuctVAVReheat",
        ],
        "missing_exact_classes": [],
        "next_work": "Build after CAV reheat so terminal assignment can be reused.",
    },
    {
        "id": "four_pipe_fan_coil",
        "name": "Four-pipe fan coil zone system",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": ["ZoneHVAC:FourPipeFanCoil"],
        "ironbug_classes": [
            "IB_ZoneHVACFourPipeFanCoil",
            "IB_CoilCoolingWater",
            "IB_CoilHeatingWater",
            "IB_FanOnOff",
        ],
        "missing_exact_classes": [],
        "next_work": "Use the single-zone seed Garden before expanding to multi-zone.",
    },
    {
        "id": "water_to_air_heat_pump",
        "name": "Water-to-air heat pump zone system",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": ["ZoneHVAC:WaterToAirHeatPump"],
        "ironbug_classes": [
            "IB_ZoneHVACWaterToAirHeatPump",
            "IB_CoilCoolingWaterToAirHeatPumpEquationFit",
            "IB_CoilHeatingWaterToAirHeatPumpEquationFit",
            "IB_FanOnOff",
        ],
        "missing_exact_classes": [],
        "next_work": "Pair with source-backed condenser/plant loop objects.",
    },
    {
        "id": "variable_refrigerant_flow",
        "name": "Variable refrigerant flow system",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "AirConditioner:VariableRefrigerantFlow",
            "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow",
        ],
        "ironbug_classes": [
            "IB_AirConditionerVariableRefrigerantFlow",
            "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow",
            "IB_CoilCoolingDXVariableRefrigerantFlow",
            "IB_CoilHeatingDXVariableRefrigerantFlow",
            "IB_FanConstantVolume",
        ],
        "missing_exact_classes": [],
        "next_work": "Probe terminal list and master thermostat wiring.",
    },
    {
        "id": "hydronic_radiant",
        "name": "Hydronic low-temperature radiant system",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "ZoneHVAC:LowTemperatureRadiant:VariableFlow",
            "ZoneHVAC:LowTemperatureRadiant:ConstantFlow",
        ],
        "ironbug_classes": [
            "IB_ZoneHVACLowTempRadiantVarFlow",
            "IB_ZoneHVACLowTempRadiantConstFlow",
            "IB_CoilCoolingLowTempRadiantVarFlow",
            "IB_CoilHeatingLowTempRadiantVarFlow",
            "IB_BoilerHotWater",
            "IB_ChillerElectricEIR",
        ],
        "missing_exact_classes": [],
        "next_work": "Start from plant-loop probes, then connect radiant zone equipment.",
    },
    {
        "id": "ptac_pthp",
        "name": "Packaged terminal air conditioner / heat pump",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "ZoneHVAC:PackagedTerminalAirConditioner",
            "ZoneHVAC:PackagedTerminalHeatPump",
        ],
        "ironbug_classes": [
            "IB_ZoneHVACPackagedTerminalAirConditioner",
            "IB_ZoneHVACPackagedTerminalHeatPump",
            "IB_CoilCoolingDXSingleSpeed",
            "IB_CoilHeatingDXSingleSpeed",
            "IB_CoilHeatingElectric",
            "IB_FanOnOff",
        ],
        "missing_exact_classes": [],
        "next_work": "Use as the first DX zone-equipment smoke test.",
    },
    {
        "id": "unit_ventilator",
        "name": "Unit ventilator zone systems",
        "status": "source-backed-needs-translator-probe",
        "energyplus_reference": [
            "ZoneHVAC:UnitVentilator",
            "Unit ventilator cooling-only/heating-only/cooling-heating variants",
        ],
        "ironbug_classes": [
            "IB_ZoneHVACUnitVentilator_CoolingOnly",
            "IB_ZoneHVACUnitVentilator_HeatingOnly",
            "IB_ZoneHVACUnitVentilator_CoolingHeating",
            "IB_CoilCoolingWater",
            "IB_CoilHeatingWater",
            "IB_FanConstantVolume",
        ],
        "missing_exact_classes": [],
        "next_work": "Probe after CAV/VAV terminal routing is stable.",
    },
]


def describe_plant_application_guide_advanced_coverage() -> dict[str, Any]:
    """Return source-backed metadata gates for advanced Plant Application Guide cases."""

    return PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_MATRIX


def describe_energyplus_hvac_system_roadmap() -> list[dict[str, Any]]:
    """Return the ordered source-backed EnergyPlus HVAC system implementation queue."""

    return ENERGYPLUS_HVAC_SYSTEM_ROADMAP


__all__ = [
    "ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_2_URL",
    "ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_3_URL",
    "ENERGYPLUS_HVAC_SYSTEM_ROADMAP",
    "PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_MATRIX",
    "PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_STATUSES",
    "describe_energyplus_hvac_system_roadmap",
    "describe_plant_application_guide_advanced_coverage",
]
