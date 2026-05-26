'MCP tool for detailed_hvac_setpoint_manager_outdoor_air_reset.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_outdoor_air_reset tool.'

    @mcp.tool(
        name='setpoint_manager_outdoor_air_reset',
        description=(
            'Create IB_SetpointManagerOutdoorAirReset / EnergyPlus SetpointManager:OutdoorAirReset. The manager resets a node setpoint from outdoor low/high temperature breakpoints, optional second reset curve values, and an optional schedule. This authors Ironbug DetailedHVAC input only; it is not an economizer, outdoor-air controller, weather file reader, result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'outdoor-air', 'outdoor-air-reset', 'reset', 'schedule', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_outdoor_air_reset(
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
            Field(description="Stable identifier for the new IB_SetpointManagerOutdoorAirReset object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        setpointat_outdoor_high_temperature: Annotated[
            float | None,
            Field(
                description="Optional node setpoint in deg C when outdoor air is at the high outdoor temperature breakpoint; maps to Ironbug field SetpointatOutdoorHighTemperature."
            ),
        ] = None,
        outdoor_high_temperature: Annotated[
            float | None,
            Field(
                description="Optional high outdoor-air temperature breakpoint in deg C; maps to Ironbug field OutdoorHighTemperature."
            ),
        ] = None,
        setpointat_outdoor_low_temperature: Annotated[
            float | None,
            Field(
                description="Optional node setpoint in deg C when outdoor air is at the low outdoor temperature breakpoint; maps to Ironbug field SetpointatOutdoorLowTemperature."
            ),
        ] = None,
        outdoor_low_temperature: Annotated[
            float | None,
            Field(
                description="Optional low outdoor-air temperature breakpoint in deg C; maps to Ironbug field OutdoorLowTemperature."
            ),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(description='Optional controlled setpoint variable, typically Temperature, MaximumTemperature, or MinimumTemperature; maps to Ironbug field ControlVariable.'),
        ] = None,
        schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug schedule target that gates the outdoor-air reset manager; pass a target dict from a schedule tool or a same-model identifier. Maps to Ironbug field Schedule.'),
        ] = None,
        setpointat_outdoor_low_temperature2: Annotated[
            float | None,
            Field(description='Optional second-curve node setpoint in deg C at the low outdoor-air breakpoint; maps to Ironbug field SetpointatOutdoorLowTemperature2.'),
        ] = None,
        outdoor_low_temperature2: Annotated[
            float | None,
            Field(description='Optional second-curve low outdoor-air temperature breakpoint in deg C; maps to Ironbug field OutdoorLowTemperature2.'),
        ] = None,
        setpointat_outdoor_high_temperature2: Annotated[
            float | None,
            Field(description='Optional second-curve node setpoint in deg C at the high outdoor-air breakpoint; maps to Ironbug field SetpointatOutdoorHighTemperature2.'),
        ] = None,
        outdoor_high_temperature2: Annotated[
            float | None,
            Field(description='Optional second-curve high outdoor-air temperature breakpoint in deg C; maps to Ironbug field OutdoorHighTemperature2.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerOutdoorAirReset field Name.'),
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
        """Create an Ironbug SetpointManager:OutdoorAirReset target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if setpointat_outdoor_high_temperature is not None:
            source_fields['SetpointatOutdoorHighTemperature'] = setpointat_outdoor_high_temperature
        if outdoor_high_temperature is not None:
            source_fields['OutdoorHighTemperature'] = outdoor_high_temperature
        if setpointat_outdoor_low_temperature is not None:
            source_fields['SetpointatOutdoorLowTemperature'] = setpointat_outdoor_low_temperature
        if outdoor_low_temperature is not None:
            source_fields['OutdoorLowTemperature'] = outdoor_low_temperature
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        if schedule_target is not None:
            source_field_targets['Schedule'] = schedule_target
        if setpointat_outdoor_low_temperature2 is not None:
            source_fields['SetpointatOutdoorLowTemperature2'] = setpointat_outdoor_low_temperature2
        if outdoor_low_temperature2 is not None:
            source_fields['OutdoorLowTemperature2'] = outdoor_low_temperature2
        if setpointat_outdoor_high_temperature2 is not None:
            source_fields['SetpointatOutdoorHighTemperature2'] = setpointat_outdoor_high_temperature2
        if outdoor_high_temperature2 is not None:
            source_fields['OutdoorHighTemperature2'] = outdoor_high_temperature2
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerOutdoorAirReset',
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
