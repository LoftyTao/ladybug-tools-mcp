'MCP tool for detailed_hvac_fan_on_off.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_fan_on_off tool.'

    @mcp.tool(
        name='fan_on_off',
        description=(
            'Create IB_FanOnOff, an Ironbug on/off or cycling HVAC fan component '
            'that maps downstream to EnergyPlus Fan:OnOff and OpenStudio FanOnOff. '
            'Use it as a supply fan target for FCU, PTAC, PTHP, unit ventilator, '
            'water-heater heat-pump, or other DetailedHVAC equipment that accepts '
            'Fan:OnOff behavior. This authors Ironbug DetailedHVAC input, not a '
            'Honeybee Energy HVAC template. Returns target, summary_view, '
            'persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'fan', 'author'},
        timeout=20,
    )
    def create_ironbug_fan_on_off(
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
            Field(description="Stable identifier for the new IB_FanOnOff object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the fan available.'),
        ] = None,
        fan_total_efficiency: Annotated[
            float | None,
            Field(description='Optional FanTotalEfficiency for the EnergyPlus/OpenStudio Fan:OnOff object; use a fraction greater than 0 and at most 1.'),
        ] = None,
        pressure_rise: Annotated[
            float | None,
            Field(description='Optional fan pressure rise in pascals; maps to Ironbug IB_FanOnOff field PressureRise.'),
        ] = None,
        maximum_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional maximum air flow rate in m3/s or Autosize where supported by the downstream OpenStudio/EnergyPlus context.'),
        ] = None,
        motor_efficiency: Annotated[
            float | None,
            Field(description='Optional motor efficiency fraction for the Fan:OnOff object; maps to Ironbug MotorEfficiency.'),
        ] = None,
        motor_in_airstream_fraction: Annotated[
            float | None,
            Field(description='Optional fraction of motor heat added to the air stream, from 0 outside the air stream to 1 inside it.'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EndUseSubcategory value; maps to Ironbug IB_FanOnOff field EndUseSubcategory.'),
        ] = None,
        fan_power_ratio_functionof_speed_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for FanPowerRatioFunctionofSpeedRatioCurve; pass a detailed_hvac curve target dict or a same-model identifier.'),
        ] = None,
        fan_efficiency_ratio_functionof_speed_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for FanEfficiencyRatioFunctionofSpeedRatioCurve; pass a detailed_hvac curve target dict or a same-model identifier.'),
        ] = None,
        fan_efficiency: Annotated[
            str | float | int | bool | None,
            Field(description='Optional FanEfficiency value; maps to Ironbug IB_FanOnOff field FanEfficiency.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_FanOnOff field Name.'),
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
        """Create IB_FanOnOff as a reviewed Ironbug on/off fan component."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fan_efficiency is not None:
            source_fields['FanEfficiency'] = fan_efficiency
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if fan_total_efficiency is not None:
            source_fields['FanTotalEfficiency'] = fan_total_efficiency
        if pressure_rise is not None:
            source_fields['PressureRise'] = pressure_rise
        if maximum_flow_rate is not None:
            source_fields['MaximumFlowRate'] = maximum_flow_rate
        if motor_efficiency is not None:
            source_fields['MotorEfficiency'] = motor_efficiency
        if motor_in_airstream_fraction is not None:
            source_fields['MotorInAirstreamFraction'] = motor_in_airstream_fraction
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if fan_power_ratio_functionof_speed_ratio_curve_target is not None:
            source_field_targets['FanPowerRatioFunctionofSpeedRatioCurve'] = fan_power_ratio_functionof_speed_ratio_curve_target
        if fan_efficiency_ratio_functionof_speed_ratio_curve_target is not None:
            source_field_targets['FanEfficiencyRatioFunctionofSpeedRatioCurve'] = fan_efficiency_ratio_functionof_speed_ratio_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_FanOnOff',
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
