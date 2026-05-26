'MCP tool for detailed_hvac_water_heater_heat_pump.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_heater_heat_pump tool.'

    @mcp.tool(
        name='water_heater_heat_pump',
        description=(
            'Create IB_WaterHeaterHeatPump, the Ironbug heat pump water heater (HPWH) compound object corresponding to EnergyPlus WaterHeater:HeatPump:* behavior. Use it with a water heater tank, an air-to-water water-heating coil, and a fan; the optional ThermalZone binding is a convenience for Ironbug ZoneEquipments, but this is not an air terminal and not a hydronic Pump:* object. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'water-heater',
            'heat-pump',
            'hpwh',
            'air-to-water',
            'compound-object',
            'zone-equipment',
            'fan',
            'hot-water',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_water_heater_heat_pump(
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
            Field(description="Stable identifier for the new IB_WaterHeaterHeatPump object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        compressor_setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CompressorSetpointTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field CompressorSetpointTemperatureSchedule (IB_Schedule).'),
        ] = None,
        dead_band_temperature_difference: Annotated[
            float | None,
            Field(description='Optional heat pump compressor cut-in dead band in deltaC; maps to DeadBandTemperatureDifference.'),
        ] = None,
        condenser_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional condenser water flow rate through the HPWH water coil in m3/s, or EnergyPlus Autocalculate text; maps to CondenserWaterFlowRate.'),
        ] = None,
        evaporator_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional evaporator air flow rate across the HPWH air coil in m3/s, or EnergyPlus Autocalculate text; maps to EvaporatorAirFlowRate.'),
        ] = None,
        inlet_air_configuration: Annotated[
            str | None,
            Field(description='Optional EnergyPlus inlet air configuration such as Schedule, ZoneAirOnly, OutdoorAirOnly, or ZoneAndOutdoorAir; maps to InletAirConfiguration.'),
        ] = None,
        inlet_air_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for InletAirTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field InletAirTemperatureSchedule (IB_Schedule).'),
        ] = None,
        inlet_air_humidity_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for InletAirHumiditySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field InletAirHumiditySchedule (IB_Schedule).'),
        ] = None,
        minimum_inlet_air_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional minimum inlet air temperature in C for HPWH compressor operation; maps to MinimumInletAirTemperatureforCompressorOperation.'),
        ] = None,
        maximum_inlet_air_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional maximum inlet air temperature in C for HPWH compressor operation; maps to MaximumInletAirTemperatureforCompressorOperation.'),
        ] = None,
        compressor_location: Annotated[
            str | None,
            Field(description='Optional EnergyPlus compressor location choice for parasitic heat accounting; maps to CompressorLocation.'),
        ] = None,
        compressor_ambient_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CompressorAmbientTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field CompressorAmbientTemperatureSchedule (IB_Schedule).'),
        ] = None,
        fan_placement: Annotated[
            str | None,
            Field(description='Optional HPWH fan placement such as BlowThrough or DrawThrough; maps to FanPlacement.'),
        ] = None,
        on_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional on-cycle parasitic electric load in W; maps to OnCycleParasiticElectricLoad.'),
        ] = None,
        off_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional off-cycle parasitic electric load in W; maps to OffCycleParasiticElectricLoad.'),
        ] = None,
        parasitic_heat_rejection_location: Annotated[
            str | None,
            Field(description='Optional ParasiticHeatRejectionLocation value; maps to Ironbug IB_WaterHeaterHeatPump field ParasiticHeatRejectionLocation.'),
        ] = None,
        inlet_air_mixer_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for InletAirMixerSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterHeatPump field InletAirMixerSchedule (IB_Schedule).'),
        ] = None,
        tank_element_control_logic: Annotated[
            str | None,
            Field(description='Optional TankElementControlLogic value; maps to Ironbug IB_WaterHeaterHeatPump field TankElementControlLogic.'),
        ] = None,
        control_sensor_location_in_stratified_tank: Annotated[
            str | None,
            Field(description='Optional ControlSensorLocationInStratifiedTank value; maps to Ironbug IB_WaterHeaterHeatPump field ControlSensorLocationInStratifiedTank.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier. When provided, the "
                    "created zone equipment is added to that ThermalZone's ZoneEquipments."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_WaterHeaterHeatPump field Name.'),
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
        water_heater_mixed_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for the WaterHeater:Mixed tank child "
                    "Parameter 'Water Heater Mixed' on IB_WaterHeaterHeatPump."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for the air-to-water water-heating coil "
                    "Parameter 'HeatingCoil' on IB_WaterHeaterHeatPump."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'Fan' "
                    "on IB_WaterHeaterHeatPump."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_WaterHeaterHeatPump as a reviewed Ironbug ZoneEquipments authoring object."""

        child_targets = [
            water_heater_mixed_target,
            heating_coil_target,
            fan_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if compressor_setpoint_temperature_schedule_target is not None:
            source_field_targets['CompressorSetpointTemperatureSchedule'] = compressor_setpoint_temperature_schedule_target
        if dead_band_temperature_difference is not None:
            source_fields['DeadBandTemperatureDifference'] = dead_band_temperature_difference
        if condenser_water_flow_rate is not None:
            source_fields['CondenserWaterFlowRate'] = condenser_water_flow_rate
        if evaporator_air_flow_rate is not None:
            source_fields['EvaporatorAirFlowRate'] = evaporator_air_flow_rate
        if inlet_air_configuration is not None:
            source_fields['InletAirConfiguration'] = inlet_air_configuration
        if inlet_air_temperature_schedule_target is not None:
            source_field_targets['InletAirTemperatureSchedule'] = inlet_air_temperature_schedule_target
        if inlet_air_humidity_schedule_target is not None:
            source_field_targets['InletAirHumiditySchedule'] = inlet_air_humidity_schedule_target
        if minimum_inlet_air_temperaturefor_compressor_operation is not None:
            source_fields['MinimumInletAirTemperatureforCompressorOperation'] = minimum_inlet_air_temperaturefor_compressor_operation
        if maximum_inlet_air_temperaturefor_compressor_operation is not None:
            source_fields['MaximumInletAirTemperatureforCompressorOperation'] = maximum_inlet_air_temperaturefor_compressor_operation
        if compressor_location is not None:
            source_fields['CompressorLocation'] = compressor_location
        if compressor_ambient_temperature_schedule_target is not None:
            source_field_targets['CompressorAmbientTemperatureSchedule'] = compressor_ambient_temperature_schedule_target
        if fan_placement is not None:
            source_fields['FanPlacement'] = fan_placement
        if on_cycle_parasitic_electric_load is not None:
            source_fields['OnCycleParasiticElectricLoad'] = on_cycle_parasitic_electric_load
        if off_cycle_parasitic_electric_load is not None:
            source_fields['OffCycleParasiticElectricLoad'] = off_cycle_parasitic_electric_load
        if parasitic_heat_rejection_location is not None:
            source_fields['ParasiticHeatRejectionLocation'] = parasitic_heat_rejection_location
        if inlet_air_mixer_schedule_target is not None:
            source_field_targets['InletAirMixerSchedule'] = inlet_air_mixer_schedule_target
        if tank_element_control_logic is not None:
            source_fields['TankElementControlLogic'] = tank_element_control_logic
        if control_sensor_location_in_stratified_tank is not None:
            source_fields['ControlSensorLocationInStratifiedTank'] = control_sensor_location_in_stratified_tank
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterHeaterHeatPump',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if thermal_zone_target is not None:
            zone = add_ironbug_thermal_zone_equipment(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                zone_equipment_target=created["target"],
            )
            latest_model_target = zone["updated_model_target"]
            created["target"]["model_target"] = latest_model_target
            binding_summary["thermal_zone_bound"] = True
            binding_summary["thermal_zone_identifier"] = zone["summary_view"][
                "thermal_zone_identifier"
            ]
        else:
            binding_summary["thermal_zone_bound"] = False
        created["updated_model_target"] = latest_model_target
        created["summary_view"] = {**created["summary_view"], **binding_summary}
        return created
