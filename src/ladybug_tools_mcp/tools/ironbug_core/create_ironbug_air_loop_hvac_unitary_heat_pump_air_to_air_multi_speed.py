'MCP tool for detailed_hvac_air_loop_unitary_heat_pump_air_to_air_multi_speed.'

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
    'Register the detailed_hvac_air_loop_unitary_heat_pump_air_to_air_multi_speed tool.'

    @mcp.tool(
        name='air_loop_unitary_heat_pump_air_to_air_multi_speed',
        description=(
            'Create IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed, the Ironbug and EnergyPlus AirLoopHVAC:UnitaryHeatPump:AirToAir:MultiSpeed object for a multi-speed unitary air-to-air heat pump on an air loop. Use it with multi-speed DX cooling/heating coils, a supply fan, optional heat recovery water flow, and a supplemental heater; it is DetailedHVAC equipment, not an Energy HVAC template and not a hydronic Pump:* object. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'air-loop',
            'unitary',
            'heat-pump',
            'air-to-air',
            'multi-speed',
            'dx',
            'fan',
            'heat-recovery',
            'supplemental-heat',
            'heating',
            'cooling',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_air_loop_hvac_unitary_heat_pump_air_to_air_multi_speed(
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
            Field(description="Stable identifier for the new IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        supply_air_fan_placement: Annotated[
            str | None,
            Field(description='Optional EnergyPlus supply fan placement such as BlowThrough or DrawThrough; maps to SupplyAirFanPlacement.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field SupplyAirFanOperatingModeSchedule (IB_Schedule).'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional outdoor dry-bulb limit in C below which compressor operation is disabled; maps to MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        maximum_supply_air_temperaturefrom_supplemental_heater: Annotated[
            float | str | None,
            Field(description='Optional maximum supply air temperature from the supplemental heater in C, or EnergyPlus Autosize text; maps to MaximumSupplyAirTemperaturefromSupplementalHeater.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation.'),
        ] = None,
        auxiliary_on_cycle_electric_power: Annotated[
            float | None,
            Field(description='Optional AuxiliaryOnCycleElectricPower value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field AuxiliaryOnCycleElectricPower.'),
        ] = None,
        auxiliary_off_cycle_electric_power: Annotated[
            float | None,
            Field(description='Optional AuxiliaryOffCycleElectricPower value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field AuxiliaryOffCycleElectricPower.'),
        ] = None,
        design_heat_recovery_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional design heat recovery water flow rate in m3/s for the plant heat-recovery connection; maps to DesignHeatRecoveryWaterFlowRate.'),
        ] = None,
        maximum_temperaturefor_heat_recovery: Annotated[
            float | None,
            Field(description='Optional maximum heat recovery water temperature in C; maps to MaximumTemperatureforHeatRecovery.'),
        ] = None,
        supply_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        numberof_speedsfor_heating: Annotated[
            int | None,
            Field(description='Optional count of heating speeds, typically 1 through 4 in EnergyPlus; maps to NumberofSpeedsforHeating.'),
        ] = None,
        numberof_speedsfor_cooling: Annotated[
            int | None,
            Field(description='Optional count of cooling speeds, typically 1 through 4 in EnergyPlus; maps to NumberofSpeedsforCooling.'),
        ] = None,
        speed1_supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed1SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed1SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        speed2_supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed2SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed2SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        speed3_supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed3SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed3SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        speed4_supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed4SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed4SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        speed1_supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed1SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed1SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        speed2_supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed2SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed2SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        speed3_supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed3SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed3SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        speed4_supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional Speed4SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Speed4SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed field Name.'),
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
                    "Optional Ironbug target for component Parameter 'CoolingCoil' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for component Parameter 'HeatingCoil' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for component Parameter 'Fan' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed."
                )
            ),
        ] = None,
        supplemental_heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for component Parameter "
                    "'SupplementalHeatingCoil' on "
                    "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed."
                )
            ),
        ] = None,
        controlling_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'ControllingZone' "
                    "on IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed as a reviewed Ironbug Loop Objs authoring object."""

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
        if supply_air_fan_placement is not None:
            source_fields['SupplyAirFanPlacement'] = supply_air_fan_placement
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if maximum_supply_air_temperaturefrom_supplemental_heater is not None:
            source_fields['MaximumSupplyAirTemperaturefromSupplementalHeater'] = maximum_supply_air_temperaturefrom_supplemental_heater
        if maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation
        if auxiliary_on_cycle_electric_power is not None:
            source_fields['AuxiliaryOnCycleElectricPower'] = auxiliary_on_cycle_electric_power
        if auxiliary_off_cycle_electric_power is not None:
            source_fields['AuxiliaryOffCycleElectricPower'] = auxiliary_off_cycle_electric_power
        if design_heat_recovery_water_flow_rate is not None:
            source_fields['DesignHeatRecoveryWaterFlowRate'] = design_heat_recovery_water_flow_rate
        if maximum_temperaturefor_heat_recovery is not None:
            source_fields['MaximumTemperatureforHeatRecovery'] = maximum_temperaturefor_heat_recovery
        if supply_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded'] = supply_air_flow_rate_when_no_coolingor_heatingis_needed
        if numberof_speedsfor_heating is not None:
            source_fields['NumberofSpeedsforHeating'] = numberof_speedsfor_heating
        if numberof_speedsfor_cooling is not None:
            source_fields['NumberofSpeedsforCooling'] = numberof_speedsfor_cooling
        if speed1_supply_air_flow_rate_during_heating_operation is not None:
            source_fields['Speed1SupplyAirFlowRateDuringHeatingOperation'] = speed1_supply_air_flow_rate_during_heating_operation
        if speed2_supply_air_flow_rate_during_heating_operation is not None:
            source_fields['Speed2SupplyAirFlowRateDuringHeatingOperation'] = speed2_supply_air_flow_rate_during_heating_operation
        if speed3_supply_air_flow_rate_during_heating_operation is not None:
            source_fields['Speed3SupplyAirFlowRateDuringHeatingOperation'] = speed3_supply_air_flow_rate_during_heating_operation
        if speed4_supply_air_flow_rate_during_heating_operation is not None:
            source_fields['Speed4SupplyAirFlowRateDuringHeatingOperation'] = speed4_supply_air_flow_rate_during_heating_operation
        if speed1_supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['Speed1SupplyAirFlowRateDuringCoolingOperation'] = speed1_supply_air_flow_rate_during_cooling_operation
        if speed2_supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['Speed2SupplyAirFlowRateDuringCoolingOperation'] = speed2_supply_air_flow_rate_during_cooling_operation
        if speed3_supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['Speed3SupplyAirFlowRateDuringCoolingOperation'] = speed3_supply_air_flow_rate_during_cooling_operation
        if speed4_supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['Speed4SupplyAirFlowRateDuringCoolingOperation'] = speed4_supply_air_flow_rate_during_cooling_operation
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed',
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
