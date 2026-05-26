'MCP tool for detailed_hvac_coil_cooling_low_temp_radiant_var_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_low_temp_radiant_var_flow tool.'

    @mcp.tool(
        name='coil_cooling_low_temp_radiant_var_flow',
        description=(
            'Create IB_CoilCoolingLowTempRadiantVarFlow, a hydronic chilled-water cooling coil child for ZoneHVACLowTempRadiantVarFlow and EnergyPlus ZoneHVAC:LowTemperatureRadiant:VariableFlow. Use it with detailed_hvac_zone_equipment_low_temp_radiant_var_flow and connect the water-side target to a plant-loop demand branch. Variable-flow radiant systems throttle chilled-water flow to meet the radiant cooling control. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'radiant', 'low-temperature', 'hydronic', 'variable-flow', 'cooling', 'chilled-water', 'plant-loop', 'zone-equipment', 'condensation', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_low_temp_radiant_var_flow(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_CoilCoolingLowTempRadiantVarFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        maximum_cold_water_flow: Annotated[
            float | str | None,
            Field(description='Optional maximum chilled-water flow rate through the variable-flow radiant cooling coil. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field MaximumColdWaterFlow.'),
        ] = None,
        cooling_control_throttling_range: Annotated[
            float | None,
            Field(description='Optional throttling range for variable-flow radiant cooling control. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CoolingControlThrottlingRange.'),
        ] = None,
        cooling_control_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for variable-flow radiant cooling control temperature. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CoolingControlTemperatureSchedule.'),
        ] = None,
        condensation_control_type: Annotated[
            str | None,
            Field(description='Optional condensation control algorithm for the radiant cooling surface. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CondensationControlType.'),
        ] = None,
        condensation_control_dewpoint_offset: Annotated[
            float | None,
            Field(description='Optional dewpoint offset for radiant cooling condensation control in C. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CondensationControlDewpointOffset.'),
        ] = None,
        cooling_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional method for specifying the radiant cooling design capacity. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CoolingDesignCapacityMethod.'),
        ] = None,
        cooling_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional radiant cooling design capacity in watts, or autosize. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CoolingDesignCapacity.'),
        ] = None,
        cooling_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional radiant cooling design capacity per floor area. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field CoolingDesignCapacityPerFloorArea.'),
        ] = None,
        fractionof_autosized_cooling_design_capacity: Annotated[
            float | None,
            Field(description='Optional fraction of autosized radiant cooling design capacity. Maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field FractionofAutosizedCoolingDesignCapacity.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingLowTempRadiantVarFlow field Name.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit Ironbug output variable names for this object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets for CustomSensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets for CustomActuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."
            ),
        ] = None,
        high_air_temperature: Annotated[
            float | None,
            Field(description='Optional default high cooling control air temperature in C used when authoring constant schedules. Stored as Ironbug property AirHiT.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilCoolingLowTempRadiantVarFlow as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if maximum_cold_water_flow is not None:
            source_fields['MaximumColdWaterFlow'] = maximum_cold_water_flow
        if cooling_control_throttling_range is not None:
            source_fields['CoolingControlThrottlingRange'] = cooling_control_throttling_range
        if cooling_control_temperature_schedule_target is not None:
            source_field_targets['CoolingControlTemperatureSchedule'] = cooling_control_temperature_schedule_target
        if condensation_control_type is not None:
            source_fields['CondensationControlType'] = condensation_control_type
        if condensation_control_dewpoint_offset is not None:
            source_fields['CondensationControlDewpointOffset'] = condensation_control_dewpoint_offset
        if cooling_design_capacity_method is not None:
            source_fields['CoolingDesignCapacityMethod'] = cooling_design_capacity_method
        if cooling_design_capacity is not None:
            source_fields['CoolingDesignCapacity'] = cooling_design_capacity
        if cooling_design_capacity_per_floor_area is not None:
            source_fields['CoolingDesignCapacityPerFloorArea'] = cooling_design_capacity_per_floor_area
        if fractionof_autosized_cooling_design_capacity is not None:
            source_fields['FractionofAutosizedCoolingDesignCapacity'] = fractionof_autosized_cooling_design_capacity
        ib_properties: dict[str, Any] = {}
        if high_air_temperature is not None:
            ib_properties['AirHiT'] = high_air_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingLowTempRadiantVarFlow',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
