'MCP tool for detailed_hvac_controller_outdoor_air.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_controller_mechanical_ventilation,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_controller_outdoor_air tool.'

    @mcp.tool(
        name='controller_outdoor_air',
        description=(
            'Create IB_ControllerOutdoorAir, the EnergyPlus Controller:OutdoorAir object for mixed-air box outdoor air flow, economizer operation, high humidity control, and heat recovery bypass control. For DOAS and ventilation air loops, first create IB_ControllerMechanicalVentilation and pass it as mechanical_ventilation_target; then pass this controller to outdoor_air_system.controller_outdoor_air_target. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'controller', 'outdoor-air', 'mixed-air', 'economizer', 'heat-recovery', 'humidity-control', 'mechanical-ventilation', 'ventilation', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_controller_outdoor_air(
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
            Field(description="Stable identifier for the new IB_ControllerOutdoorAir object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio name for this outdoor air controller. Maps to Ironbug IB_ControllerOutdoorAir field Name."
            ),
        ] = None,
        minimum_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(
                description="Optional minimum outdoor air flow rate for the air loop, in m3/s or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_ControllerOutdoorAir field MinimumOutdoorAirFlowRate."
            ),
        ] = None,
        economizer_control_type: Annotated[
            str | None,
            Field(
                description="Optional outdoor air economizer control type, such as NoEconomizer, FixedDryBulb, DifferentialDryBulb, or ElectronicEnthalpy. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerControlType."
            ),
        ] = None,
        high_humidity_control: Annotated[
            bool | str | None,
            Field(
                description="Optional high indoor humidity control flag for modifying outdoor air flow when humidistat control is active. Maps to Ironbug IB_ControllerOutdoorAir field HighHumidityControl."
            ),
        ] = None,
        mechanical_ventilation_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ControllerMechanicalVentilation target or same-model identifier "
                    "to attach as this outdoor-air controller's mechanical ventilation child. "
                    "Use it when the air loop needs ASHRAE 62.1, IAQP, or DCV minimum "
                    "outdoor air calculations before applying DetailedHVAC."
                )
            ),
        ] = None,
        minimum_outdoor_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier that multiplies the minimum outdoor air flow rate. Maps to Ironbug IB_ControllerOutdoorAir field MinimumOutdoorAirSchedule.'),
        ] = None,
        minimum_fractionof_outdoor_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the minimum outdoor air fraction of current system flow. Maps to Ironbug IB_ControllerOutdoorAir field MinimumFractionofOutdoorAirSchedule.'),
        ] = None,
        maximum_fractionof_outdoor_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the maximum outdoor air fraction of current system flow. Maps to Ironbug IB_ControllerOutdoorAir field MaximumFractionofOutdoorAirSchedule.'),
        ] = None,
        timeof_day_economizer_control_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier that enables time-of-day economizer outdoor air boost when schedule values are above 0. Maps to Ironbug IB_ControllerOutdoorAir field TimeofDayEconomizerControlSchedule.'),
        ] = None,
        maximum_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional maximum outdoor air flow rate for the controller, in m3/s or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_ControllerOutdoorAir field MaximumOutdoorAirFlowRate.'),
        ] = None,
        economizer_control_action_type: Annotated[
            str | None,
            Field(description='Optional economizer action type, such as ModulateFlow or MinimumFlowWithBypass for heat-exchanger bypass workflows. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerControlActionType.'),
        ] = None,
        economizer_maximum_limit_dry_bulb_temperature: Annotated[
            float | None,
            Field(description='Optional outdoor dry-bulb high limit in degrees C for economizer operation. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerMaximumLimitDryBulbTemperature.'),
        ] = None,
        economizer_maximum_limit_enthalpy: Annotated[
            float | None,
            Field(description='Optional outdoor air enthalpy high limit for economizer operation, in J/kg. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerMaximumLimitEnthalpy.'),
        ] = None,
        economizer_maximum_limit_dewpoint_temperature: Annotated[
            float | None,
            Field(description='Optional outdoor dewpoint high limit in degrees C for economizer operation. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerMaximumLimitDewpointTemperature.'),
        ] = None,
        electronic_enthalpy_limit_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target or same-model identifier for electronic enthalpy economizer humidity-ratio limits. Maps to Ironbug IB_ControllerOutdoorAir field ElectronicEnthalpyLimitCurve.'),
        ] = None,
        economizer_minimum_limit_dry_bulb_temperature: Annotated[
            float | None,
            Field(description='Optional outdoor dry-bulb low limit in degrees C for economizer operation. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerMinimumLimitDryBulbTemperature.'),
        ] = None,
        lockout_type: Annotated[
            str | None,
            Field(description='Optional economizer lockout type, such as NoLockout, LockoutWithHeating, or LockoutWithCompressor. Maps to Ironbug IB_ControllerOutdoorAir field LockoutType.'),
        ] = None,
        minimum_limit_type: Annotated[
            str | None,
            Field(description='Optional minimum outdoor air limit type, such as FixedMinimum or ProportionalMinimum. Maps to Ironbug IB_ControllerOutdoorAir field MinimumLimitType.'),
        ] = None,
        high_humidity_outdoor_air_flow_ratio: Annotated[
            float | None,
            Field(description='Optional ratio applied to maximum outdoor air flow during high humidity control. Maps to Ironbug IB_ControllerOutdoorAir field HighHumidityOutdoorAirFlowRatio.'),
        ] = None,
        control_high_indoor_humidity_based_on_outdoor_humidity_ratio: Annotated[
            bool | str | None,
            Field(description='Optional flag for activating high indoor humidity control only when outdoor humidity ratio is lower than indoor humidity ratio. Maps to Ironbug IB_ControllerOutdoorAir field ControlHighIndoorHumidityBasedOnOutdoorHumidityRatio.'),
        ] = None,
        heat_recovery_bypass_control_type: Annotated[
            str | None,
            Field(description='Optional heat recovery bypass control type used with outdoor air economizer or high humidity control. Maps to Ironbug IB_ControllerOutdoorAir field HeatRecoveryBypassControlType.'),
        ] = None,
        economizer_operation_staging: Annotated[
            str | None,
            Field(description='Optional economizer staging mode for air loops with unitary multi-speed cooling equipment. Maps to Ironbug IB_ControllerOutdoorAir field EconomizerOperationStaging.'),
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
        """Create IB_ControllerOutdoorAir as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if minimum_outdoor_air_flow_rate is not None:
            source_fields['MinimumOutdoorAirFlowRate'] = minimum_outdoor_air_flow_rate
        if economizer_control_type is not None:
            source_fields['EconomizerControlType'] = economizer_control_type
        if high_humidity_control is not None:
            source_fields['HighHumidityControl'] = high_humidity_control
        source_properties: dict[str, Any] = {}
        if minimum_outdoor_air_schedule_target is not None:
            source_field_targets['MinimumOutdoorAirSchedule'] = minimum_outdoor_air_schedule_target
        if minimum_fractionof_outdoor_air_schedule_target is not None:
            source_field_targets['MinimumFractionofOutdoorAirSchedule'] = minimum_fractionof_outdoor_air_schedule_target
        if maximum_fractionof_outdoor_air_schedule_target is not None:
            source_field_targets['MaximumFractionofOutdoorAirSchedule'] = maximum_fractionof_outdoor_air_schedule_target
        if timeof_day_economizer_control_schedule_target is not None:
            source_field_targets['TimeofDayEconomizerControlSchedule'] = timeof_day_economizer_control_schedule_target
        if maximum_outdoor_air_flow_rate is not None:
            source_fields['MaximumOutdoorAirFlowRate'] = maximum_outdoor_air_flow_rate
        if economizer_control_action_type is not None:
            source_fields['EconomizerControlActionType'] = economizer_control_action_type
        if economizer_maximum_limit_dry_bulb_temperature is not None:
            source_fields['EconomizerMaximumLimitDryBulbTemperature'] = economizer_maximum_limit_dry_bulb_temperature
        if economizer_maximum_limit_enthalpy is not None:
            source_fields['EconomizerMaximumLimitEnthalpy'] = economizer_maximum_limit_enthalpy
        if economizer_maximum_limit_dewpoint_temperature is not None:
            source_fields['EconomizerMaximumLimitDewpointTemperature'] = economizer_maximum_limit_dewpoint_temperature
        if electronic_enthalpy_limit_curve_target is not None:
            source_field_targets['ElectronicEnthalpyLimitCurve'] = electronic_enthalpy_limit_curve_target
        if economizer_minimum_limit_dry_bulb_temperature is not None:
            source_fields['EconomizerMinimumLimitDryBulbTemperature'] = economizer_minimum_limit_dry_bulb_temperature
        if lockout_type is not None:
            source_fields['LockoutType'] = lockout_type
        if minimum_limit_type is not None:
            source_fields['MinimumLimitType'] = minimum_limit_type
        if high_humidity_outdoor_air_flow_ratio is not None:
            source_fields['HighHumidityOutdoorAirFlowRatio'] = high_humidity_outdoor_air_flow_ratio
        if control_high_indoor_humidity_based_on_outdoor_humidity_ratio is not None:
            source_fields['ControlHighIndoorHumidityBasedOnOutdoorHumidityRatio'] = control_high_indoor_humidity_based_on_outdoor_humidity_ratio
        if heat_recovery_bypass_control_type is not None:
            source_fields['HeatRecoveryBypassControlType'] = heat_recovery_bypass_control_type
        if economizer_operation_staging is not None:
            source_fields['EconomizerOperationStaging'] = economizer_operation_staging
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ControllerOutdoorAir',
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
        if mechanical_ventilation_target is None:
            created["summary_view"] = {
                **created["summary_view"],
                "mechanical_ventilation_bound": False,
            }
            return created

        updated = set_ironbug_controller_mechanical_ventilation(
            garden_root=garden_root,
            ironbug_model_target=created["updated_model_target"],
            controller_outdoor_air_target=created["target"],
            controller_mechanical_ventilation_target=mechanical_ventilation_target,
        )
        created["target"] = updated["target"]
        created["updated_model_target"] = updated["updated_model_target"]
        created["summary_view"] = {
            **created["summary_view"],
            "mechanical_ventilation_bound": True,
            "mechanical_ventilation_identifier": updated["summary_view"][
                "mechanical_ventilation_identifier"
            ],
        }
        return created
