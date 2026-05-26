'MCP tool for detailed_hvac_fan_system_model.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_fan_system_model tool.'

    @mcp.tool(
        name='fan_system_model',
        description=(
            'Create an Ironbug IB_FanSystemModel component for the versatile EnergyPlus/OpenStudio Fan:SystemModel system model fan in a DetailedHVAC graph. Use this when a fan needs continuous or discrete speed control, constant-volume or variable-air-volume behavior, power sizing methods, a flow-fraction curve, or night-ventilation settings. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'fan',
            'system-model',
            'air-loop',
            'curve',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_fan_system_model(
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
            Field(description="Stable DetailedHVAC object identifier for this Fan:SystemModel component."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        speeds: Annotated[
            str | float | int | bool | None,
            Field(
                description="Optional discrete speed data accepted by Ironbug's Speeds property; source Grasshopper examples use comma-separated flowFraction,electricPowerFraction pairs such as '0.33,0.12', each fraction from 0 to 1."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier for the fan availability schedule; schedule values greater than 0 make the fan available."),
        ] = None,
        design_maximum_air_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional design maximum air flow rate in m3/s, or autosize-compatible value accepted by the Ironbug source mirror."),
        ] = None,
        speed_control_method: Annotated[
            str | None,
            Field(description="Optional EnergyPlus speed control method, typically Continuous or Discrete."),
        ] = None,
        electric_power_minimum_flow_rate_fraction: Annotated[
            float | None,
            Field(description="Optional minimum flow fraction for electric power, from 0 to 1."),
        ] = None,
        design_pressure_rise: Annotated[
            float | None,
            Field(description="Optional design fan pressure rise in Pa."),
        ] = None,
        motor_efficiency: Annotated[
            float | None,
            Field(description="Optional motor efficiency as a 0-1 fraction."),
        ] = None,
        motor_in_air_stream_fraction: Annotated[
            float | None,
            Field(description="Optional motor heat fraction added to the air stream, from 0 outside air stream to 1 fully in air stream."),
        ] = None,
        design_electric_power_consumption: Annotated[
            float | str | None,
            Field(description="Optional design electric power consumption in W, or autosize-compatible value accepted by the Ironbug source mirror."),
        ] = None,
        design_power_sizing_method: Annotated[
            str | None,
            Field(description="Optional EnergyPlus sizing method, usually PowerPerFlow, PowerPerFlowPerPressure, or TotalEfficiencyAndPressure."),
        ] = None,
        electric_power_per_unit_flow_rate: Annotated[
            float | None,
            Field(description="Optional electric power per unit flow rate in W/(m3/s)."),
        ] = None,
        electric_power_per_unit_flow_rate_per_unit_pressure: Annotated[
            float | None,
            Field(description="Optional electric power per unit flow rate per unit pressure in W/((m3/s)-Pa)."),
        ] = None,
        fan_total_efficiency: Annotated[
            float | None,
            Field(description="Optional fan total efficiency as a 0-1 fraction."),
        ] = None,
        electric_power_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for the electric-power function of normalized flow fraction."),
        ] = None,
        night_ventilation_mode_pressure_rise: Annotated[
            float | None,
            Field(description="Optional fan pressure rise in Pa when used by AvailabilityManager:NightVentilation."),
        ] = None,
        night_ventilation_mode_flow_fraction: Annotated[
            float | None,
            Field(description="Optional night-ventilation flow fraction of design maximum air flow, from 0 to 1."),
        ] = None,
        motor_loss_radiative_fraction: Annotated[
            float | None,
            Field(description="Optional radiative fraction of motor skin losses assigned to a motor-loss zone, from 0 to 1."),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description="Optional EnergyPlus end-use subcategory text, such as General or Supply Fans."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional EnergyPlus/OpenStudio fan name; defaults to the identifier when omitted."),
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
        """Create IB_FanSystemModel as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if design_maximum_air_flow_rate is not None:
            source_fields['DesignMaximumAirFlowRate'] = design_maximum_air_flow_rate
        if speed_control_method is not None:
            source_fields['SpeedControlMethod'] = speed_control_method
        if electric_power_minimum_flow_rate_fraction is not None:
            source_fields['ElectricPowerMinimumFlowRateFraction'] = electric_power_minimum_flow_rate_fraction
        if design_pressure_rise is not None:
            source_fields['DesignPressureRise'] = design_pressure_rise
        if motor_efficiency is not None:
            source_fields['MotorEfficiency'] = motor_efficiency
        if motor_in_air_stream_fraction is not None:
            source_fields['MotorInAirStreamFraction'] = motor_in_air_stream_fraction
        if design_electric_power_consumption is not None:
            source_fields['DesignElectricPowerConsumption'] = design_electric_power_consumption
        if design_power_sizing_method is not None:
            source_fields['DesignPowerSizingMethod'] = design_power_sizing_method
        if electric_power_per_unit_flow_rate is not None:
            source_fields['ElectricPowerPerUnitFlowRate'] = electric_power_per_unit_flow_rate
        if electric_power_per_unit_flow_rate_per_unit_pressure is not None:
            source_fields['ElectricPowerPerUnitFlowRatePerUnitPressure'] = electric_power_per_unit_flow_rate_per_unit_pressure
        if fan_total_efficiency is not None:
            source_fields['FanTotalEfficiency'] = fan_total_efficiency
        if electric_power_functionof_flow_fraction_curve_target is not None:
            source_field_targets['ElectricPowerFunctionofFlowFractionCurve'] = electric_power_functionof_flow_fraction_curve_target
        if night_ventilation_mode_pressure_rise is not None:
            source_fields['NightVentilationModePressureRise'] = night_ventilation_mode_pressure_rise
        if night_ventilation_mode_flow_fraction is not None:
            source_fields['NightVentilationModeFlowFraction'] = night_ventilation_mode_flow_fraction
        if motor_loss_radiative_fraction is not None:
            source_fields['MotorLossRadiativeFraction'] = motor_loss_radiative_fraction
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if speeds is not None:
            source_properties['Speeds'] = speeds
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_FanSystemModel',
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
