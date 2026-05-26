'MCP tool for detailed_hvac_setpoint_manager_scheduled.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_scheduled tool.'

    @mcp.tool(
        name='setpoint_manager_scheduled',
        description=(
            'Create IB_SetpointManagerScheduled / EnergyPlus SetpointManager:Scheduled for node setpoints driven by a schedule or a constant Value. Use control_variable for Temperature, HumidityRatio, MassFlowRate, or other supported EnergyPlus control variables, and pass schedule_target when a ScheduleRuleset or ScheduleFile should drive the setpoint. This authors Ironbug DetailedHVAC input only; it is not a ScheduleRuleset creator, dual setpoint manager, thermostat, result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'scheduled-setpoint', 'schedule', 'temperature', 'humidity-ratio', 'air-loop', 'plant-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_scheduled(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json; for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_SetpointManagerScheduled object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus control variable for the scheduled setpoint, such as Temperature, HumidityRatio, or MassFlowRate; maps to Ironbug field ControlVariable."
            ),
        ] = None,
        value: Annotated[
            float | None,
            Field(
                description="Optional constant setpoint value used by Ironbug to create a ScheduleRuleset when schedule_target is not supplied; maps to source property Value."
            ),
        ] = None,
        is_temperature: Annotated[
            bool | None,
            Field(
                description="Optional flag telling Ironbug whether Value should create a temperature schedule; maps to source property IsTemperature."
            ),
        ] = None,
        schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug schedule target, such as ScheduleRuleset or ScheduleFile, that drives the setpoint values. Maps to Ironbug field Schedule.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerScheduled field Name.'),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:Scheduled target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if schedule_target is not None:
            source_field_targets['Schedule'] = schedule_target
        if value is not None:
            source_properties['Value'] = value
        if is_temperature is not None:
            source_properties['IsTemperature'] = is_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerScheduled',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
