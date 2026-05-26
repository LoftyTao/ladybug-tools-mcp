'MCP tool for detailed_hvac_coil_cooling_low_temp_radiant_const_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_low_temp_radiant_const_flow tool.'

    @mcp.tool(
        name='coil_cooling_low_temp_radiant_const_flow',
        description=(
            'Create IB_CoilCoolingLowTempRadiantConstFlow, a hydronic chilled-water cooling coil child for ZoneHVACLowTempRadiantConstFlow and EnergyPlus ZoneHVAC:LowTemperatureRadiant:ConstantFlow. Use it with detailed_hvac_zone_equipment_low_temp_radiant_const_flow and connect the water-side target to a plant-loop demand branch. Constant-flow radiant systems control inlet water temperature from water and control temperature schedules. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'radiant', 'low-temperature', 'hydronic', 'constant-flow', 'cooling', 'chilled-water', 'plant-loop', 'zone-equipment', 'condensation', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_low_temp_radiant_const_flow(
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
            Field(description="Stable identifier for the new IB_CoilCoolingLowTempRadiantConstFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        cooling_high_water_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the constant-flow radiant cooling high water temperature. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CoolingHighWaterTemperatureSchedule.'),
        ] = None,
        cooling_low_water_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the constant-flow radiant cooling low water temperature. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CoolingLowWaterTemperatureSchedule.'),
        ] = None,
        cooling_high_control_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the high control temperature used by the radiant cooling water reset. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CoolingHighControlTemperatureSchedule.'),
        ] = None,
        cooling_low_control_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the low control temperature used by the radiant cooling water reset. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CoolingLowControlTemperatureSchedule.'),
        ] = None,
        condensation_control_type: Annotated[
            str | None,
            Field(description='Optional condensation control algorithm for the radiant cooling surface. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CondensationControlType.'),
        ] = None,
        condensation_control_dewpoint_offset: Annotated[
            float | None,
            Field(description='Optional dewpoint offset for radiant cooling condensation control in C. Maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field CondensationControlDewpointOffset.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingLowTempRadiantConstFlow field Name.'),
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
        high_water_temperature: Annotated[
            float | None,
            Field(description='Optional default high chilled-water temperature in C used when authoring constant schedules. Stored as Ironbug property WaterHiT.'),
        ] = None,
        low_water_temperature: Annotated[
            float | None,
            Field(description='Optional default low chilled-water temperature in C used when authoring constant schedules. Stored as Ironbug property WaterLoT.'),
        ] = None,
        high_air_temperature: Annotated[
            float | None,
            Field(description='Optional default high cooling control air temperature in C used when authoring constant schedules. Stored as Ironbug property AirHiT.'),
        ] = None,
        low_air_temperature: Annotated[
            float | None,
            Field(description='Optional default low cooling control air temperature in C used when authoring constant schedules. Stored as Ironbug property AirLoT.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilCoolingLowTempRadiantConstFlow as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if cooling_high_water_temperature_schedule_target is not None:
            source_field_targets['CoolingHighWaterTemperatureSchedule'] = cooling_high_water_temperature_schedule_target
        if cooling_low_water_temperature_schedule_target is not None:
            source_field_targets['CoolingLowWaterTemperatureSchedule'] = cooling_low_water_temperature_schedule_target
        if cooling_high_control_temperature_schedule_target is not None:
            source_field_targets['CoolingHighControlTemperatureSchedule'] = cooling_high_control_temperature_schedule_target
        if cooling_low_control_temperature_schedule_target is not None:
            source_field_targets['CoolingLowControlTemperatureSchedule'] = cooling_low_control_temperature_schedule_target
        if condensation_control_type is not None:
            source_fields['CondensationControlType'] = condensation_control_type
        if condensation_control_dewpoint_offset is not None:
            source_fields['CondensationControlDewpointOffset'] = condensation_control_dewpoint_offset
        ib_properties: dict[str, Any] = {}
        if low_air_temperature is not None:
            ib_properties['AirLoT'] = low_air_temperature
        if high_air_temperature is not None:
            ib_properties['AirHiT'] = high_air_temperature
        if low_water_temperature is not None:
            ib_properties['WaterLoT'] = low_water_temperature
        if high_water_temperature is not None:
            ib_properties['WaterHiT'] = high_water_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingLowTempRadiantConstFlow',
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
