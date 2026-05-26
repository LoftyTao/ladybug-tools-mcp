'MCP tool for detailed_hvac_air_loop_unitary_heat_pump_air_to_air.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object


def _target_identifier(target: dict[str, Any] | str) -> str:
    if isinstance(target, str):
        return target
    identifier = target.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("controlling_zone_target requires an Ironbug target identifier.")
    return identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_loop_unitary_heat_pump_air_to_air tool.'

    @mcp.tool(
        name='air_loop_unitary_heat_pump_air_to_air',
        description=(
            'Create IB_AirLoopHVACUnitaryHeatPumpAirToAir, the Ironbug and EnergyPlus AirLoopHVAC:UnitaryHeatPump:AirToAir object for a single-speed unitary air-to-air heat pump on an air loop. Use it with DX cooling, DX air-to-air heating, a supply fan, and an optional supplemental heating coil; it is DetailedHVAC equipment, not an Energy HVAC template and not a hydronic Pump:* object. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'air-loop',
            'unitary',
            'heat-pump',
            'air-to-air',
            'dx',
            'fan',
            'supplemental-heat',
            'heating',
            'cooling',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_air_loop_hvac_unitary_heat_pump_air_to_air(
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
            Field(description="Stable identifier for the new IB_AirLoopHVACUnitaryHeatPumpAirToAir object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAir field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional cooling supply air flow rate in m3/s, or EnergyPlus Autosize/Autocalculate text when supported; maps to SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional heating supply air flow rate in m3/s, or EnergyPlus Autosize/Autocalculate text when supported; maps to SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional no-load supply air flow rate in m3/s for continuous-fan operation; maps to SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        maximum_supply_air_temperaturefrom_supplemental_heater: Annotated[
            float | str | None,
            Field(description='Optional maximum supply air temperature from the supplemental heater in C, or EnergyPlus Autosize text; maps to MaximumSupplyAirTemperaturefromSupplementalHeater.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation: Annotated[
            float | None,
            Field(description='Optional outdoor dry-bulb limit in C above which supplemental heat is disabled; maps to MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation.'),
        ] = None,
        fan_placement: Annotated[
            str | None,
            Field(description='Optional EnergyPlus fan placement such as BlowThrough or DrawThrough; maps to FanPlacement.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAir field SupplyAirFanOperatingModeSchedule (IB_Schedule).'),
        ] = None,
        dehumidification_control_type: Annotated[
            str | None,
            Field(description='Optional EnergyPlus dehumidification control type for the unitary heat pump; maps to DehumidificationControlType.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAir field Name.'),
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
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for the DX cooling coil child Parameter "
                    "'CoolingCoil' on IB_AirLoopHVACUnitaryHeatPumpAirToAir."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for the DX air-to-air heating coil child "
                    "Parameter 'HeatingCoil' on IB_AirLoopHVACUnitaryHeatPumpAirToAir."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for component Parameter 'Fan' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAir."
                )
            ),
        ] = None,
        supplemental_heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for the supplemental heating coil child "
                    "Parameter 'SupplementalHeatingCoil' on IB_AirLoopHVACUnitaryHeatPumpAirToAir."
                )
            ),
        ] = None,
        controlling_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'ControllingZone' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAir."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirLoopHVACUnitaryHeatPumpAirToAir as a reviewed Ironbug Loop Objs authoring object."""

        child_targets = [
            cooling_coil_target,
            heating_coil_target,
            fan_target,
            supplemental_heating_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        ib_properties: dict[str, Any] = {}
        if controlling_zone_target is not None:
            ib_properties["_controlZoneName"] = _target_identifier(controlling_zone_target)
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRateDuringCoolingOperation'] = supply_air_flow_rate_during_cooling_operation
        if supply_air_flow_rate_during_heating_operation is not None:
            source_fields['SupplyAirFlowRateDuringHeatingOperation'] = supply_air_flow_rate_during_heating_operation
        if supply_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded'] = supply_air_flow_rate_when_no_coolingor_heatingis_needed
        if maximum_supply_air_temperaturefrom_supplemental_heater is not None:
            source_fields['MaximumSupplyAirTemperaturefromSupplementalHeater'] = maximum_supply_air_temperaturefrom_supplemental_heater
        if maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation
        if fan_placement is not None:
            source_fields['FanPlacement'] = fan_placement
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        if dehumidification_control_type is not None:
            source_fields['DehumidificationControlType'] = dehumidification_control_type
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirLoopHVACUnitaryHeatPumpAirToAir',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
