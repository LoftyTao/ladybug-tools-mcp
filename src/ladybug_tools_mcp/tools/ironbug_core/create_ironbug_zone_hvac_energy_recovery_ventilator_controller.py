"""MCP tool for IB_ZoneHVACEnergyRecoveryVentilatorController."""

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the ERV controller authoring tool."""

    @mcp.tool(
        name="IB_zone_hvac_energy_recovery_ventilator_controller",
        description=(
            "Create IB_ZoneHVACEnergyRecoveryVentilatorController, the controller "
            "for an EnergyPlus ZoneHVAC:EnergyRecoveryVentilator. Set temperature, "
            "enthalpy, dewpoint, exhaust-air, high-humidity, economizer curve, and "
            "time-of-day schedule limits; pass the returned target to "
            "IB_zone_equipment_energy_recovery_ventilator.controller_target. Returns "
            "target, summary_view, persistence_receipt, and report for downstream "
            "DetailedHVAC assembly. This tool authors Ironbug DetailedHVAC input "
            "only; run Energy simulation with the standard Ladybug Tools MCP Energy "
            "workflow after DetailedHVAC is applied."
        ),
        tags={
            "ironbug",
            "detailed-hvac",
            "hvac",
            "component",
            "controller",
            "energy-recovery",
            "heat-recovery",
            "ventilation",
            "zone-equipment",
            "author",
        },
        timeout=20,
    )
    def create_ironbug_zone_hvac_energy_recovery_ventilator_controller(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target returned by IB_create_model; "
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description=(
                    "Stable identifier for the new "
                    "IB_ZoneHVACEnergyRecoveryVentilatorController object."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        temperature_high_limit: Annotated[
            float | None,
            Field(
                description=(
                    "Optional high outdoor-air temperature limit in degrees C. "
                    "Maps to TemperatureHighLimit."
                )
            ),
        ] = None,
        temperature_low_limit: Annotated[
            float | None,
            Field(
                description=(
                    "Optional low outdoor-air temperature limit in degrees C. "
                    "Maps to TemperatureLowLimit."
                )
            ),
        ] = None,
        enthalpy_high_limit: Annotated[
            float | None,
            Field(
                description="Optional high outdoor-air enthalpy limit. Maps to EnthalpyHighLimit.",
            ),
        ] = None,
        dewpoint_temperature_limit: Annotated[
            float | None,
            Field(
                description=(
                    "Optional high outdoor-air dewpoint limit in degrees C. "
                    "Maps to DewpointTemperatureLimit."
                )
            ),
        ] = None,
        electronic_enthalpy_limit_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_Curve target or same-model identifier used for "
                    "the electronic enthalpy limit. Maps to "
                    "ElectronicEnthalpyLimitCurve."
                )
            ),
        ] = None,
        exhaust_air_temperature_limit: Annotated[
            str | None,
            Field(
                description=(
                    "Optional exhaust-air temperature limit value. Maps to "
                    "ExhaustAirTemperatureLimit."
                )
            ),
        ] = None,
        exhaust_air_enthalpy_limit: Annotated[
            str | None,
            Field(
                description=(
                    "Optional exhaust-air enthalpy limit value. Maps to "
                    "ExhaustAirEnthalpyLimit."
                )
            ),
        ] = None,
        timeof_day_economizer_flow_control_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_Schedule target or same-model identifier for the "
                    "time-of-day economizer flow-control schedule. Maps to "
                    "TimeofDayEconomizerFlowControlSchedule."
                )
            ),
        ] = None,
        high_humidity_control_flag: Annotated[
            bool | str | None,
            Field(
                description=(
                    "Optional high-humidity control flag. Maps to "
                    "HighHumidityControlFlag."
                )
            ),
        ] = None,
        high_humidity_outdoor_air_flow_ratio: Annotated[
            float | None,
            Field(
                description=(
                    "Optional outdoor-air flow ratio during high-humidity control. "
                    "Maps to HighHumidityOutdoorAirFlowRatio."
                )
            ),
        ] = None,
        control_high_indoor_humidity_based_on_outdoor_humidity_ratio: Annotated[
            bool | str | None,
            Field(
                description=(
                    "Optional flag to control high indoor humidity based on the "
                    "outdoor humidity ratio. Maps to "
                    "ControlHighIndoorHumidityBasedonOutdoorHumidityRatio."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Name value; maps to the Ironbug "
                    "IB_ZoneHVACEnergyRecoveryVentilatorController Name field."
                )
            ),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(description="Optional explicit Ironbug output variable names."),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemInternalVariable targets."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an ERV controller with optional typed curve and schedule targets."""

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_object

        source_fields: dict[str, Any] = {}
        if name is not None:
            source_fields["Name"] = name
        for field_name, value in {
            "TemperatureHighLimit": temperature_high_limit,
            "TemperatureLowLimit": temperature_low_limit,
            "EnthalpyHighLimit": enthalpy_high_limit,
            "DewpointTemperatureLimit": dewpoint_temperature_limit,
            "ExhaustAirTemperatureLimit": exhaust_air_temperature_limit,
            "ExhaustAirEnthalpyLimit": exhaust_air_enthalpy_limit,
            "HighHumidityControlFlag": high_humidity_control_flag,
            "HighHumidityOutdoorAirFlowRatio": high_humidity_outdoor_air_flow_ratio,
            "ControlHighIndoorHumidityBasedonOutdoorHumidityRatio": (
                control_high_indoor_humidity_based_on_outdoor_humidity_ratio
            ),
        }.items():
            if value is not None:
                source_fields[field_name] = value

        source_field_targets: dict[str, Any] = {}
        if electronic_enthalpy_limit_curve_target is not None:
            source_field_targets[
                "ElectronicEnthalpyLimitCurve"
            ] = electronic_enthalpy_limit_curve_target
        if timeof_day_economizer_flow_control_schedule_target is not None:
            source_field_targets[
                "TimeofDayEconomizerFlowControlSchedule"
            ] = timeof_day_economizer_flow_control_schedule_target

        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_ZoneHVACEnergyRecoveryVentilatorController",
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
