"""Source-backed Ironbug plant archetypes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ironbug.hvac import (
    IB_ChillerElectricEIR,
    IB_CoolingTowerSingleSpeed,
    IB_CoolingTowerVariableSpeed,
    IB_DistrictCooling,
    IB_HVACObject,
    IB_HVACSystem,
    IB_HeatExchangerFluidToFluid,
    IB_LoadProfilePlant,
    IB_Model,
    IB_PipeAdiabatic,
    IB_PlantEquipmentOperationCoolingLoad,
    IB_PlantLoop,
    IB_PlantLoopBranches,
    IB_PumpConstantSpeed,
    IB_PumpVariableSpeed,
    IB_SetpointManagerScheduled,
    IB_SizingPlant,
)
from ironbug.hvac.operation_schemes import (
    PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
    plant_equipment_operation_ib_properties,
)
from ironbug.plant_application_guide import (
    ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_2_URL,
    ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_3_URL,
    PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_MATRIX,
    PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_STATUSES,
    describe_plant_application_guide_advanced_coverage,
)


ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_1_URL = (
    "https://bigladdersoftware.com/epx/docs/25-1/plant-application-guide/"
    "example-01-chiller-and-condenser-loops.html"
)
PLANT_APPLICATION_GUIDE_EXAMPLE_1_MAPPING: dict[str, Any] = {
    "energyplus_reference": {
        "guide": "EnergyPlus Plant Application Guide",
        "version": "25.1",
        "example": "Example System 1: Chiller and Condenser Loops",
        "idf_name": "PlantApplicationsGuide_Example1.idf",
        "url": ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_1_URL,
        "source_summary": (
            "The example uses one chilled water PlantLoop with a water-cooled "
            "electric chiller and load profile, plus one condenser PlantLoop "
            "with a cooling tower."
        ),
    },
    "source_backed_objects": [
        {
            "role": "chilled_water_loop",
            "energyplus_objects": ["PlantLoop"],
            "ironbug_class": "IB_PlantLoop",
            "source_path": "src/Ironbug.HVAC/Loops/IB_PlantLoop.cs",
            "required_source_fields": ["Name", "FluidType"],
            "source_properties": ["SizingPlant", "OperationScheme"],
        },
        {
            "role": "condenser_loop",
            "energyplus_objects": ["PlantLoop"],
            "ironbug_class": "IB_PlantLoop",
            "source_path": "src/Ironbug.HVAC/Loops/IB_PlantLoop.cs",
            "required_source_fields": ["Name", "FluidType"],
            "source_properties": ["SizingPlant", "OperationScheme"],
        },
        {
            "role": "plant_branch_group",
            "energyplus_objects": ["Branch", "BranchList"],
            "ironbug_class": "IB_PlantLoopBranches",
            "source_path": "src/Ironbug.HVAC/Loops/IB_PlantLoopBranches.cs",
            "required_source_fields": [],
            "source_properties": [],
            "source_base_properties": {
                "IB_LoopBranches": ["Branches"],
            },
        },
        {
            "role": "constant_speed_pump",
            "energyplus_objects": ["Pump:ConstantSpeed"],
            "ironbug_class": "IB_PumpConstantSpeed",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_PumpConstantSpeed.cs",
            "required_source_fields": [
                "RatedPumpHead",
                "MotorEfficiency",
                "RatedFlowRate",
                "PumpControlType",
            ],
            "source_properties": [],
        },
        {
            "role": "water_cooled_chiller",
            "energyplus_objects": ["Chiller:Electric:EIR"],
            "ironbug_class": "IB_ChillerElectricEIR",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_ChillerElectricEIR.cs",
            "required_source_fields": [
                "Name",
                "ReferenceCapacity",
                "ReferenceCOP",
                "CondenserType",
                "ReferenceLeavingChilledWaterTemperature",
            ],
            "source_properties": [],
        },
        {
            "role": "cooling_tower",
            "energyplus_objects": ["CoolingTower:VariableSpeed"],
            "ironbug_class": "IB_CoolingTowerVariableSpeed",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_CoolingTowerVariableSpeed.cs",
            "required_source_fields": [
                "DesignWaterFlowRate",
                "DesignAirFlowRate",
                "DesignFanPower",
            ],
            "source_properties": [],
        },
        {
            "role": "load_profile",
            "energyplus_objects": ["LoadProfile:Plant"],
            "ironbug_class": "IB_LoadProfilePlant",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_LoadProfilePlant.cs",
            "required_source_fields": [],
            "source_properties": [],
        },
        {
            "role": "cooling_load_operation_scheme",
            "energyplus_objects": ["PlantEquipmentOperation:CoolingLoad"],
            "ironbug_class": "IB_PlantEquipmentOperationCoolingLoad",
            "source_path": (
                "src/Ironbug.HVAC/LoopObjs/"
                "IB_PlantEquipmentOperationCoolingLoad.cs"
            ),
            "required_source_fields": [],
            "source_properties": [],
            "source_method_dependencies": [
                "IB_PlantEquipmentOperationSchemeBase.AddEquipment",
            ],
            "source_binding": {
                "property": "IBProperties._equipments",
                "item_source_class": (
                    "IB_PlantEquipmentOperationSchemeBase."
                    "PlantEquipmentOperationSchemeItem"
                ),
                "item_fields": ["Limit", "Obj"],
                "default_upper_limit_w": PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
            },
            "python_schema_note": (
                "Equipment limit/object pairs are modeled through the same "
                "serialized backing property used by the source-side "
                "AddEquipment(limit, obj) method, not as top-level public "
                "Limit/Obj fields on the operation scheme."
            ),
        },
        {
            "role": "loop_setpoint",
            "energyplus_objects": ["SetpointManager:Scheduled"],
            "ironbug_class": "IB_SetpointManagerScheduled",
            "source_path": (
                "src/Ironbug.HVAC/SetpointManagers/"
                "IB_SetpointManagerScheduled.cs"
            ),
            "required_source_fields": ["ControlVariable"],
            "source_properties": ["Value", "IsTemperature"],
        },
        {
            "role": "loop_sizing",
            "energyplus_objects": ["Sizing:Plant"],
            "ironbug_class": "IB_SizingPlant",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_SizingPlant.cs",
            "required_source_fields": [
                "LoopType",
                "DesignLoopExitTemperature",
                "LoopDesignTemperatureDifference",
            ],
            "source_properties": [],
        },
        {
            "role": "bypass_pipe",
            "energyplus_objects": ["Pipe:Adiabatic"],
            "ironbug_class": "IB_PipeAdiabatic",
            "source_path": "src/Ironbug.HVAC/LoopObjs/IB_PipeAdiabatic.cs",
            "required_source_fields": ["Name"],
            "source_properties": [],
        },
    ],
    "not_directly_source_backed": {
        "plant_connectors": {
            "energyplus_objects": [
                "Branch",
                "BranchList",
                "Connector:Splitter",
                "Connector:Mixer",
                "ConnectorList",
            ],
            "ironbug_representation": "IB_PlantLoopBranches.Branches",
            "boundary": (
                "Ironbug source does not expose an IB_Connector object. "
                "Connector splitter/mixer behavior is generated by the branch "
                "group during source-side OpenStudio translation."
            ),
        },
        "runtime_execution": {
            "energyplus_objects": ["OSM", "IDF", "SQL", "ERR"],
            "ironbug_representation": None,
            "boundary": (
                "This archetype is source-backed ibjson authoring only. It is "
                "not an EnergyPlus simulation result until a DetailedHVAC plant "
                "loop translator exists."
            ),
        },
    },
}


def _fields(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _constant_speed_pump(identifier: str) -> IB_PumpConstantSpeed:
    return IB_PumpConstantSpeed(
        identifier=identifier,
        CustomAttributes=_fields(
            RatedPumpHead=179352,
            MotorEfficiency=0.9,
            RatedFlowRate="Autosize",
            PumpControlType="Intermittent",
        ),
    )


def _variable_speed_pump(identifier: str) -> IB_PumpVariableSpeed:
    return IB_PumpVariableSpeed(
        identifier=identifier,
        CustomAttributes=_fields(
            RatedPumpHead=179352,
            MotorEfficiency=0.9,
            RatedFlowRate="Autosize",
            PumpControlType="Intermittent",
            Coefficient1ofthePartLoadPerformanceCurve=0,
            Coefficient2ofthePartLoadPerformanceCurve=1,
            Coefficient3ofthePartLoadPerformanceCurve=0,
            Coefficient4ofthePartLoadPerformanceCurve=0,
        ),
    )


def _scheduled_temperature_setpoint(identifier: str, value: float) -> IB_SetpointManagerScheduled:
    return IB_SetpointManagerScheduled(
        identifier=identifier,
        CustomAttributes=_fields(ControlVariable="Temperature"),
        Value=value,
        IsTemperature=True,
    )


def _cooling_load_operation_scheme(
    identifier: str,
    equipment: IB_HVACObject,
    *,
    upper_limit_w: int = PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
) -> IB_PlantEquipmentOperationCoolingLoad:
    return IB_PlantEquipmentOperationCoolingLoad(
        identifier=identifier,
        IBProperties=plant_equipment_operation_ib_properties(
            equipment,
            upper_limit_w=upper_limit_w,
        ),
    )


def _cooling_sizing(identifier: str, exit_temperature: float) -> IB_SizingPlant:
    return IB_SizingPlant(
        identifier=identifier,
        CustomAttributes=_fields(
            LoopType="Cooling",
            DesignLoopExitTemperature=exit_temperature,
            LoopDesignTemperatureDifference=6.7,
        ),
    )


def build_primary_secondary_pumping_plant_core_archetype(
    *,
    identifier: str = "plant_app_guide_example_3_plant_core",
) -> IB_Model:
    """Build a reduced, source-backed Example 3 primary/secondary plant core."""

    heat_exchanger = IB_HeatExchangerFluidToFluid(
        identifier=f"{identifier}_fluid_to_fluid_heat_exchanger",
        display_name="Example 3 plant-core Fluid-to-Fluid Heat Exchanger",
    )

    primary_loop = IB_PlantLoop.model_construct(
        identifier=f"{identifier}_primary_chilled_water_loop",
        CustomAttributes=_fields(
            Name="Primary Chilled Water Loop",
            FluidType="Water",
        ),
        SupplyComponents=[
            _constant_speed_pump(f"{identifier}_primary_chilled_water_pump"),
            IB_DistrictCooling(
                identifier=f"{identifier}_purchased_cooling",
                CustomAttributes=_fields(
                    Name="Purchased Cooling",
                    NominalCapacity="Autosize",
                ),
            ),
        ],
        DemandComponents=[
            heat_exchanger,
        ],
    )

    secondary_loop = IB_PlantLoop.model_construct(
        identifier=f"{identifier}_secondary_chilled_water_loop",
        CustomAttributes=_fields(
            Name="Secondary Chilled Water Loop",
            FluidType="Water",
        ),
        SupplyComponents=[
            _variable_speed_pump(f"{identifier}_secondary_chilled_water_pump"),
            heat_exchanger,
        ],
        DemandComponents=[
            IB_LoadProfilePlant(identifier=f"{identifier}_secondary_load_profile"),
        ],
    )

    condenser_loop = IB_PlantLoop.model_construct(
        identifier=f"{identifier}_condenser_loop",
        CustomAttributes=_fields(
            Name="Condenser Loop",
            FluidType="Water",
        ),
        SupplyComponents=[
            _variable_speed_pump(f"{identifier}_condenser_water_pump"),
            IB_CoolingTowerSingleSpeed(
                identifier=f"{identifier}_single_speed_cooling_tower",
                CustomAttributes=_fields(NominalCapacity="Autosize"),
            ),
        ],
        DemandComponents=[],
    )

    return IB_Model(
        identifier=identifier,
        display_name=(
            "Plant Application Guide Example 3 plant-core "
            "(reduced scope, source-backed)"
        ),
        HVACSystem=IB_HVACSystem(
            AirLoops=[],
            PlantLoops=[
                primary_loop,
                secondary_loop,
                condenser_loop,
            ],
            VariableRefrigerantFlows=[],
        ),
    )


def build_chiller_condenser_loop_archetype(
    *,
    identifier: str = "plant_app_guide_example_1",
) -> IB_Model:
    """Build EnergyPlus Plant Application Guide Example 1 as source-backed ibjson."""

    chiller = IB_ChillerElectricEIR(
        identifier=f"{identifier}_water_cooled_chiller",
        CustomAttributes=_fields(
            Name="Water Cooled Chiller",
            ReferenceCapacity="Autosize",
            ReferenceCOP=5.5,
            CondenserType="WaterCooled",
            ReferenceLeavingChilledWaterTemperature=6.7,
        ),
    )
    chiller_branch = IB_PlantLoopBranches(
        identifier=f"{identifier}_chiller_branches",
        Branches=[
            [chiller],
            [
                IB_PipeAdiabatic(
                    identifier=f"{identifier}_chilled_water_bypass",
                    CustomAttributes=_fields(Name="Chilled Water Bypass Pipe"),
                )
            ],
        ],
    )
    chilled_water_loop = IB_PlantLoop.model_construct(
        identifier=f"{identifier}_chilled_water_loop",
        CustomAttributes=_fields(
            Name="Chilled Water Loop",
            FluidType="Water",
        ),
        SizingPlant=_cooling_sizing(
            f"{identifier}_chilled_water_sizing",
            exit_temperature=6.7,
        ),
        OperationScheme=_cooling_load_operation_scheme(
            identifier=f"{identifier}_cooling_operation",
            equipment=chiller,
        ),
        SupplyComponents=[
            _constant_speed_pump(f"{identifier}_chilled_water_pump"),
            chiller_branch,
            _scheduled_temperature_setpoint(
                f"{identifier}_chilled_water_setpoint",
                value=6.7,
            ),
        ],
        DemandComponents=[
            IB_LoadProfilePlant(identifier=f"{identifier}_demand_load_profile"),
        ],
    )

    cooling_tower = IB_CoolingTowerVariableSpeed(
        identifier=f"{identifier}_cooling_tower",
        CustomAttributes=_fields(
            DesignWaterFlowRate="Autosize",
            DesignAirFlowRate="Autosize",
            DesignFanPower="Autosize",
        ),
    )
    condenser_loop = IB_PlantLoop.model_construct(
        identifier=f"{identifier}_condenser_loop",
        CustomAttributes=_fields(
            Name="Condenser Loop",
            FluidType="Water",
        ),
        SizingPlant=_cooling_sizing(
            f"{identifier}_condenser_sizing",
            exit_temperature=29.4,
        ),
        OperationScheme=_cooling_load_operation_scheme(
            identifier=f"{identifier}_tower_operation",
            equipment=cooling_tower,
        ),
        SupplyComponents=[
            _constant_speed_pump(f"{identifier}_condenser_water_pump"),
            cooling_tower,
            _scheduled_temperature_setpoint(
                f"{identifier}_condenser_water_setpoint",
                value=29.4,
            ),
        ],
        DemandComponents=[
            chiller,
        ],
    )

    return IB_Model(
        identifier=identifier,
        display_name="Plant Application Guide Example 1",
        HVACSystem=IB_HVACSystem(
            AirLoops=[],
            PlantLoops=[chilled_water_loop, condenser_loop],
            VariableRefrigerantFlows=[],
        ),
    )


def describe_chiller_condenser_loop_simulation_gate() -> dict[str, Any]:
    """Describe why this archetype is not yet a claimed EnergyPlus run path."""

    return {
        "archetype": "chiller_condenser_loop",
        "energyplus_reference": PLANT_APPLICATION_GUIDE_EXAMPLE_1_MAPPING[
            "energyplus_reference"
        ],
        "ibjson_ready": True,
        "energyplus_runtime_ready": False,
        "blocking_gap": "detailed_hvac_plant_loop_translator",
        "allowed_next_step": (
            "translate source-backed Ironbug plant loops into a Honeybee/OpenStudio "
            "DetailedHVAC specification before running EnergyPlus"
        ),
    }


def write_plant_application_guide_example_1_mapping_report(
    artifact_root: str | Path,
) -> Path:
    """Write the Example 1 mapping report under a deterministic artifact root."""

    output_dir = Path(artifact_root).resolve() / "ironbug_plant_archetypes"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "plant_application_guide_example_1_mapping.json"
    output_path.write_text(
        json.dumps(
            PLANT_APPLICATION_GUIDE_EXAMPLE_1_MAPPING,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_1_URL",
    "ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_2_URL",
    "ENERGYPLUS_PLANT_APPLICATION_GUIDE_EXAMPLE_3_URL",
    "PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_MATRIX",
    "PLANT_APPLICATION_GUIDE_ADVANCED_COVERAGE_STATUSES",
    "PLANT_APPLICATION_GUIDE_EXAMPLE_1_MAPPING",
    "build_chiller_condenser_loop_archetype",
    "build_primary_secondary_pumping_plant_core_archetype",
    "describe_chiller_condenser_loop_simulation_gate",
    "describe_plant_application_guide_advanced_coverage",
    "write_plant_application_guide_example_1_mapping_report",
]
