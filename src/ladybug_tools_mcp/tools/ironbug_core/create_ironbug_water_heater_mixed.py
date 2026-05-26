'MCP tool for detailed_hvac_water_heater_mixed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_heater_mixed tool.'

    @mcp.tool(
        name='water_heater_mixed',
        description=(
            'Create IB_WaterHeaterMixed, the Ironbug and EnergyPlus WaterHeater:Mixed single-node water tank for service hot water, storage, tankless, or indirect plant-loop use. It can take schedules, fuel/capacity fields, ambient zone or schedule inputs, a part-load curve, and optional WaterHeater:Sizing child; it is not a heat-pump water heater compound object or a water-use fixture. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'plant-component', 'plant-loop', 'water-heater', 'service-hot-water', 'storage', 'schedule', 'fuel', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_water_heater_mixed(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
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
            Field(description="Stable identifier for the new IB_WaterHeaterMixed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        tank_volume: Annotated[
            float | str | None,
            Field(description='Optional tank volume in m3, or autosize/autocalculate text accepted by the source field.'),
        ] = None,
        setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for tank setpoint temperature.'),
        ] = None,
        deadband_temperature_difference: Annotated[
            float | None,
            Field(description='Optional DeadbandTemperatureDifference value; maps to Ironbug IB_WaterHeaterMixed field DeadbandTemperatureDifference.'),
        ] = None,
        maximum_temperature_limit: Annotated[
            float | None,
            Field(description='Optional MaximumTemperatureLimit value; maps to Ironbug IB_WaterHeaterMixed field MaximumTemperatureLimit.'),
        ] = None,
        heater_control_type: Annotated[
            str | None,
            Field(description='Optional HeaterControlType value; maps to Ironbug IB_WaterHeaterMixed field HeaterControlType.'),
        ] = None,
        heater_maximum_capacity: Annotated[
            float | str | None,
            Field(description='Optional HeaterMaximumCapacity value; maps to Ironbug IB_WaterHeaterMixed field HeaterMaximumCapacity.'),
        ] = None,
        heater_minimum_capacity: Annotated[
            float | None,
            Field(description='Optional HeaterMinimumCapacity value; maps to Ironbug IB_WaterHeaterMixed field HeaterMinimumCapacity.'),
        ] = None,
        heater_ignition_minimum_flow_rate: Annotated[
            float | None,
            Field(description='Optional HeaterIgnitionMinimumFlowRate value; maps to Ironbug IB_WaterHeaterMixed field HeaterIgnitionMinimumFlowRate.'),
        ] = None,
        heater_ignition_delay: Annotated[
            float | None,
            Field(description='Optional HeaterIgnitionDelay value; maps to Ironbug IB_WaterHeaterMixed field HeaterIgnitionDelay.'),
        ] = None,
        heater_fuel_type: Annotated[
            str | None,
            Field(description='Optional HeaterFuelType value; maps to Ironbug IB_WaterHeaterMixed field HeaterFuelType.'),
        ] = None,
        heater_thermal_efficiency: Annotated[
            float | None,
            Field(description='Optional HeaterThermalEfficiency value; maps to Ironbug IB_WaterHeaterMixed field HeaterThermalEfficiency.'),
        ] = None,
        part_load_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PartLoadFactorCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterMixed field PartLoadFactorCurve (IB_Curve).'),
        ] = None,
        off_cycle_parasitic_fuel_consumption_rate: Annotated[
            float | None,
            Field(description='Optional OffCycleParasiticFuelConsumptionRate value; maps to Ironbug IB_WaterHeaterMixed field OffCycleParasiticFuelConsumptionRate.'),
        ] = None,
        off_cycle_parasitic_fuel_type: Annotated[
            str | None,
            Field(description='Optional OffCycleParasiticFuelType value; maps to Ironbug IB_WaterHeaterMixed field OffCycleParasiticFuelType.'),
        ] = None,
        off_cycle_parasitic_heat_fractionto_tank: Annotated[
            float | None,
            Field(description='Optional OffCycleParasiticHeatFractiontoTank value; maps to Ironbug IB_WaterHeaterMixed field OffCycleParasiticHeatFractiontoTank.'),
        ] = None,
        on_cycle_parasitic_fuel_consumption_rate: Annotated[
            float | None,
            Field(description='Optional OnCycleParasiticFuelConsumptionRate value; maps to Ironbug IB_WaterHeaterMixed field OnCycleParasiticFuelConsumptionRate.'),
        ] = None,
        on_cycle_parasitic_fuel_type: Annotated[
            str | None,
            Field(description='Optional OnCycleParasiticFuelType value; maps to Ironbug IB_WaterHeaterMixed field OnCycleParasiticFuelType.'),
        ] = None,
        on_cycle_parasitic_heat_fractionto_tank: Annotated[
            float | None,
            Field(description='Optional OnCycleParasiticHeatFractiontoTank value; maps to Ironbug IB_WaterHeaterMixed field OnCycleParasiticHeatFractiontoTank.'),
        ] = None,
        ambient_temperature_indicator: Annotated[
            str | None,
            Field(description='Optional AmbientTemperatureIndicator value; maps to Ironbug IB_WaterHeaterMixed field AmbientTemperatureIndicator.'),
        ] = None,
        ambient_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AmbientTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterMixed field AmbientTemperatureSchedule (IB_Schedule).'),
        ] = None,
        off_cycle_loss_coefficientto_ambient_temperature: Annotated[
            float | None,
            Field(description='Optional OffCycleLossCoefficienttoAmbientTemperature value; maps to Ironbug IB_WaterHeaterMixed field OffCycleLossCoefficienttoAmbientTemperature.'),
        ] = None,
        off_cycle_loss_fractionto_thermal_zone: Annotated[
            float | None,
            Field(description='Optional OffCycleLossFractiontoThermalZone value; maps to Ironbug IB_WaterHeaterMixed field OffCycleLossFractiontoThermalZone.'),
        ] = None,
        on_cycle_loss_coefficientto_ambient_temperature: Annotated[
            float | None,
            Field(description='Optional OnCycleLossCoefficienttoAmbientTemperature value; maps to Ironbug IB_WaterHeaterMixed field OnCycleLossCoefficienttoAmbientTemperature.'),
        ] = None,
        on_cycle_loss_fractionto_thermal_zone: Annotated[
            float | None,
            Field(description='Optional OnCycleLossFractiontoThermalZone value; maps to Ironbug IB_WaterHeaterMixed field OnCycleLossFractiontoThermalZone.'),
        ] = None,
        peak_use_flow_rate: Annotated[
            float | None,
            Field(description='Optional PeakUseFlowRate value; maps to Ironbug IB_WaterHeaterMixed field PeakUseFlowRate.'),
        ] = None,
        use_flow_rate_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for UseFlowRateFractionSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterMixed field UseFlowRateFractionSchedule (IB_Schedule).'),
        ] = None,
        cold_water_supply_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ColdWaterSupplyTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterMixed field ColdWaterSupplyTemperatureSchedule (IB_Schedule).'),
        ] = None,
        use_side_effectiveness: Annotated[
            float | None,
            Field(description='Optional UseSideEffectiveness value; maps to Ironbug IB_WaterHeaterMixed field UseSideEffectiveness.'),
        ] = None,
        source_side_effectiveness: Annotated[
            float | None,
            Field(description='Optional SourceSideEffectiveness value; maps to Ironbug IB_WaterHeaterMixed field SourceSideEffectiveness.'),
        ] = None,
        use_side_design_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional UseSideDesignFlowRate value; maps to Ironbug IB_WaterHeaterMixed field UseSideDesignFlowRate.'),
        ] = None,
        source_side_design_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional SourceSideDesignFlowRate value; maps to Ironbug IB_WaterHeaterMixed field SourceSideDesignFlowRate.'),
        ] = None,
        indirect_water_heating_recovery_time: Annotated[
            float | None,
            Field(description='Optional IndirectWaterHeatingRecoveryTime value; maps to Ironbug IB_WaterHeaterMixed field IndirectWaterHeatingRecoveryTime.'),
        ] = None,
        source_side_flow_control_mode: Annotated[
            str | None,
            Field(description='Optional SourceSideFlowControlMode value; maps to Ironbug IB_WaterHeaterMixed field SourceSideFlowControlMode.'),
        ] = None,
        indirect_alternate_setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for IndirectAlternateSetpointTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterHeaterMixed field IndirectAlternateSetpointTemperatureSchedule (IB_Schedule).'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EndUseSubcategory value; maps to Ironbug IB_WaterHeaterMixed field EndUseSubcategory.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_WaterHeaterMixed field Name.'),
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
        zone: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Ironbug component Parameter 'zone_' "
                    "stored as source private property _zone."
                )
            ),
        ] = None,
        sizing_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'sizing_' "
                    "on IB_WaterHeaterMixed."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug mixed service-water heater tank."""

        child_targets = [
            sizing_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if tank_volume is not None:
            source_fields['TankVolume'] = tank_volume
        if setpoint_temperature_schedule_target is not None:
            source_field_targets['SetpointTemperatureSchedule'] = setpoint_temperature_schedule_target
        if deadband_temperature_difference is not None:
            source_fields['DeadbandTemperatureDifference'] = deadband_temperature_difference
        if maximum_temperature_limit is not None:
            source_fields['MaximumTemperatureLimit'] = maximum_temperature_limit
        if heater_control_type is not None:
            source_fields['HeaterControlType'] = heater_control_type
        if heater_maximum_capacity is not None:
            source_fields['HeaterMaximumCapacity'] = heater_maximum_capacity
        if heater_minimum_capacity is not None:
            source_fields['HeaterMinimumCapacity'] = heater_minimum_capacity
        if heater_ignition_minimum_flow_rate is not None:
            source_fields['HeaterIgnitionMinimumFlowRate'] = heater_ignition_minimum_flow_rate
        if heater_ignition_delay is not None:
            source_fields['HeaterIgnitionDelay'] = heater_ignition_delay
        if heater_fuel_type is not None:
            source_fields['HeaterFuelType'] = heater_fuel_type
        if heater_thermal_efficiency is not None:
            source_fields['HeaterThermalEfficiency'] = heater_thermal_efficiency
        if part_load_factor_curve_target is not None:
            source_field_targets['PartLoadFactorCurve'] = part_load_factor_curve_target
        if off_cycle_parasitic_fuel_consumption_rate is not None:
            source_fields['OffCycleParasiticFuelConsumptionRate'] = off_cycle_parasitic_fuel_consumption_rate
        if off_cycle_parasitic_fuel_type is not None:
            source_fields['OffCycleParasiticFuelType'] = off_cycle_parasitic_fuel_type
        if off_cycle_parasitic_heat_fractionto_tank is not None:
            source_fields['OffCycleParasiticHeatFractiontoTank'] = off_cycle_parasitic_heat_fractionto_tank
        if on_cycle_parasitic_fuel_consumption_rate is not None:
            source_fields['OnCycleParasiticFuelConsumptionRate'] = on_cycle_parasitic_fuel_consumption_rate
        if on_cycle_parasitic_fuel_type is not None:
            source_fields['OnCycleParasiticFuelType'] = on_cycle_parasitic_fuel_type
        if on_cycle_parasitic_heat_fractionto_tank is not None:
            source_fields['OnCycleParasiticHeatFractiontoTank'] = on_cycle_parasitic_heat_fractionto_tank
        if ambient_temperature_indicator is not None:
            source_fields['AmbientTemperatureIndicator'] = ambient_temperature_indicator
        if ambient_temperature_schedule_target is not None:
            source_field_targets['AmbientTemperatureSchedule'] = ambient_temperature_schedule_target
        if off_cycle_loss_coefficientto_ambient_temperature is not None:
            source_fields['OffCycleLossCoefficienttoAmbientTemperature'] = off_cycle_loss_coefficientto_ambient_temperature
        if off_cycle_loss_fractionto_thermal_zone is not None:
            source_fields['OffCycleLossFractiontoThermalZone'] = off_cycle_loss_fractionto_thermal_zone
        if on_cycle_loss_coefficientto_ambient_temperature is not None:
            source_fields['OnCycleLossCoefficienttoAmbientTemperature'] = on_cycle_loss_coefficientto_ambient_temperature
        if on_cycle_loss_fractionto_thermal_zone is not None:
            source_fields['OnCycleLossFractiontoThermalZone'] = on_cycle_loss_fractionto_thermal_zone
        if peak_use_flow_rate is not None:
            source_fields['PeakUseFlowRate'] = peak_use_flow_rate
        if use_flow_rate_fraction_schedule_target is not None:
            source_field_targets['UseFlowRateFractionSchedule'] = use_flow_rate_fraction_schedule_target
        if cold_water_supply_temperature_schedule_target is not None:
            source_field_targets['ColdWaterSupplyTemperatureSchedule'] = cold_water_supply_temperature_schedule_target
        if use_side_effectiveness is not None:
            source_fields['UseSideEffectiveness'] = use_side_effectiveness
        if source_side_effectiveness is not None:
            source_fields['SourceSideEffectiveness'] = source_side_effectiveness
        if use_side_design_flow_rate is not None:
            source_fields['UseSideDesignFlowRate'] = use_side_design_flow_rate
        if source_side_design_flow_rate is not None:
            source_fields['SourceSideDesignFlowRate'] = source_side_design_flow_rate
        if indirect_water_heating_recovery_time is not None:
            source_fields['IndirectWaterHeatingRecoveryTime'] = indirect_water_heating_recovery_time
        if source_side_flow_control_mode is not None:
            source_fields['SourceSideFlowControlMode'] = source_side_flow_control_mode
        if indirect_alternate_setpoint_temperature_schedule_target is not None:
            source_field_targets['IndirectAlternateSetpointTemperatureSchedule'] = indirect_alternate_setpoint_temperature_schedule_target
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        ib_properties: dict[str, Any] = {}
        if zone is not None:
            ib_properties['_zone'] = zone
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterHeaterMixed',
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
