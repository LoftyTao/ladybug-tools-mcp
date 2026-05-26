'MCP tool for detailed_hvac_fan_constant_volume.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_fan_constant_volume tool.'

    @mcp.tool(
        name='fan_constant_volume',
        description=(
            'Create an Ironbug IB_FanConstantVolume component for an EnergyPlus/OpenStudio Fan:ConstantVolume in a DetailedHVAC graph. Use this for scheduled constant-flow supply fans on air loops, PIU terminals, or zone HVAC equipment that accepts a constant-volume fan child. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'fan',
            'constant-volume',
            'air-loop',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_fan_constant_volume(
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
            Field(description="Stable DetailedHVAC object identifier for this constant-volume fan."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio fan name; defaults to the identifier when omitted."
            ),
        ] = None,
        fan_efficiency: Annotated[
            str | float | int | bool | None,
            Field(
                description="Optional OpenStudio fan efficiency field accepted by the Ironbug source mirror; use a 0-1 numeric value unless reproducing source data."
            ),
        ] = None,
        pressure_rise: Annotated[
            float | None,
            Field(
                description="Optional fan pressure rise in Pa for Fan:ConstantVolume."
            ),
        ] = None,
        motor_efficiency: Annotated[
            float | None,
            Field(
                description="Optional motor efficiency as a 0-1 fraction."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier for the fan availability schedule; schedule values greater than 0 make the fan available."),
        ] = None,
        fan_total_efficiency: Annotated[
            float | None,
            Field(description="Optional fan total efficiency as a 0-1 fraction for Fan:ConstantVolume."),
        ] = None,
        motor_in_airstream_fraction: Annotated[
            float | None,
            Field(description="Optional motor heat fraction added to the air stream, from 0 outside air stream to 1 fully in air stream."),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description="Optional EnergyPlus end-use subcategory text, such as General or Supply Fans."),
        ] = None,
        maximum_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional maximum air flow rate in m3/s, or autosize-compatible value accepted by the Ironbug source mirror."),
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
        """Create IB_FanConstantVolume as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fan_efficiency is not None:
            source_fields['FanEfficiency'] = fan_efficiency
        if pressure_rise is not None:
            source_fields['PressureRise'] = pressure_rise
        if motor_efficiency is not None:
            source_fields['MotorEfficiency'] = motor_efficiency
        source_properties: dict[str, Any] = {}
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if fan_total_efficiency is not None:
            source_fields['FanTotalEfficiency'] = fan_total_efficiency
        if motor_in_airstream_fraction is not None:
            source_fields['MotorInAirstreamFraction'] = motor_in_airstream_fraction
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if maximum_flow_rate is not None:
            source_fields['MaximumFlowRate'] = maximum_flow_rate
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_FanConstantVolume',
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
