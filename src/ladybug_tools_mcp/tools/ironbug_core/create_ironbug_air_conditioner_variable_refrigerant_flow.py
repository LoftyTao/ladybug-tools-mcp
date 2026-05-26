'MCP tool for detailed_hvac_air_conditioner_variable_refrigerant_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_conditioner_variable_refrigerant_flow tool.'

    @mcp.tool(
        name='air_conditioner_variable_refrigerant_flow',
        description=(
            'Create IB_AirConditionerVariableRefrigerantFlow, a VRF heat-pump system that serves zone terminal units through refrigerant flow, from the Ironbug Loops / VRF source mirror. Use terminals_targets for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow objects; do not connect this VRF system with plant-loop water-coil tools. Apply DetailedHVAC to Honeybee or Dragonfly after the VRF graph is complete. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'vrf', 'heat-pump', 'terminal-unit', 'hvac', 'author', 'zone-equipment'},
        timeout=20,
    )
    def create_ironbug_air_conditioner_variable_refrigerant_flow(
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
            Field(description="Stable identifier for the new VRF heat-pump system object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio VRF system name; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field Name."
            ),
        ] = None,
        rated_cooling_cop: Annotated[
            str | float | int | bool | None,
            Field(
                description="Optional rated cooling COP for the VRF outdoor unit; maps to Ironbug field RatedCoolingCOP."
            ),
        ] = None,
        rated_heating_cop: Annotated[
            float | None,
            Field(
                description="Optional rated heating COP for the VRF outdoor unit; maps to Ironbug field RatedHeatingCOP."
            ),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_Schedule target for BasinHeaterOperatingSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier."
            ),
        ] = None,
        cooling_capacity_ratio_boundary_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_Curve target for CoolingCapacityRatioBoundaryCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier."
            ),
        ] = None,
        terminals_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_ZoneHVACTerminalUnitVariableRefrigerantFlow targets served by this VRF system; pass detailed_hvac_zone_equipment_terminal_unit_variable_refrigerant_flow targets or same-model identifiers."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        gross_rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional GrossRatedTotalCoolingCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field GrossRatedTotalCoolingCapacity.'),
        ] = None,
        gross_rated_cooling_cop: Annotated[
            float | None,
            Field(description='Optional GrossRatedCoolingCOP value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field GrossRatedCoolingCOP.'),
        ] = None,
        rated_total_cooling_capacity: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedTotalCoolingCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field RatedTotalCoolingCapacity.'),
        ] = None,
        minimum_outdoor_temperaturein_cooling_mode: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorTemperatureinCoolingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MinimumOutdoorTemperatureinCoolingMode.'),
        ] = None,
        maximum_outdoor_temperaturein_cooling_mode: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorTemperatureinCoolingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MaximumOutdoorTemperatureinCoolingMode.'),
        ] = None,
        cooling_capacity_ratio_modifier_functionof_low_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingCapacityRatioModifierFunctionofLowTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingCapacityRatioModifierFunctionofLowTemperatureCurve (IB_Curve).'),
        ] = None,
        cooling_capacity_ratio_modifier_functionof_high_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingCapacityRatioModifierFunctionofHighTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingCapacityRatioModifierFunctionofHighTemperatureCurve (IB_Curve).'),
        ] = None,
        cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve (IB_Curve).'),
        ] = None,
        cooling_energy_input_ratio_boundary_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingEnergyInputRatioBoundaryCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioBoundaryCurve (IB_Curve).'),
        ] = None,
        cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve (IB_Curve).'),
        ] = None,
        cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        cooling_combination_ratio_correction_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingCombinationRatioCorrectionFactorCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingCombinationRatioCorrectionFactorCurve (IB_Curve).'),
        ] = None,
        cooling_part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingPartLoadFractionCorrelationCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CoolingPartLoadFractionCorrelationCurve (IB_Curve).'),
        ] = None,
        gross_rated_heating_capacity: Annotated[
            float | str | None,
            Field(description='Optional GrossRatedHeatingCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field GrossRatedHeatingCapacity.'),
        ] = None,
        rated_heating_capacity_sizing_ratio: Annotated[
            float | None,
            Field(description='Optional RatedHeatingCapacitySizingRatio value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field RatedHeatingCapacitySizingRatio.'),
        ] = None,
        rated_total_heating_capacity: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedTotalHeatingCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field RatedTotalHeatingCapacity.'),
        ] = None,
        rated_total_heating_capacity_sizing_ratio: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedTotalHeatingCapacitySizingRatio value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field RatedTotalHeatingCapacitySizingRatio.'),
        ] = None,
        minimum_outdoor_temperaturein_heating_mode: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorTemperatureinHeatingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MinimumOutdoorTemperatureinHeatingMode.'),
        ] = None,
        maximum_outdoor_temperaturein_heating_mode: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorTemperatureinHeatingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MaximumOutdoorTemperatureinHeatingMode.'),
        ] = None,
        heating_capacity_ratio_modifier_functionof_low_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingCapacityRatioModifierFunctionofLowTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioModifierFunctionofLowTemperatureCurve (IB_Curve).'),
        ] = None,
        heating_capacity_ratio_boundary_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingCapacityRatioBoundaryCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioBoundaryCurve (IB_Curve).'),
        ] = None,
        heating_capacity_ratio_modifier_functionof_high_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingCapacityRatioModifierFunctionofHighTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioModifierFunctionofHighTemperatureCurve (IB_Curve).'),
        ] = None,
        heating_energy_input_ratio_modifier_functionof_low_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve (IB_Curve).'),
        ] = None,
        heating_energy_input_ratio_boundary_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingEnergyInputRatioBoundaryCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioBoundaryCurve (IB_Curve).'),
        ] = None,
        heating_energy_input_ratio_modifier_functionof_high_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve (IB_Curve).'),
        ] = None,
        heating_performance_curve_outdoor_temperature_type_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingPerformanceCurveOutdoorTemperatureType; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingPerformanceCurveOutdoorTemperatureType (IB_Curve).'),
        ] = None,
        heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        heating_combination_ratio_correction_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingCombinationRatioCorrectionFactorCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingCombinationRatioCorrectionFactorCurve (IB_Curve).'),
        ] = None,
        heating_part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingPartLoadFractionCorrelationCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatingPartLoadFractionCorrelationCurve (IB_Curve).'),
        ] = None,
        minimum_heat_pump_part_load_ratio: Annotated[
            float | None,
            Field(
                description=(
                    "Optional MinimumHeatPumpPartLoadRatio value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MinimumHeatPumpPartLoadRatio. Defaults to 0.5 so "
                    "EnergyPlus accepts the source default low part-load ratio curves, "
                    "whose minimum x value is 0.5."
                )
            ),
        ] = 0.5,
        master_thermostat_priority_control_type: Annotated[
            str | None,
            Field(description='Optional MasterThermostatPriorityControlType value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MasterThermostatPriorityControlType.'),
        ] = None,
        thermostat_priority_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ThermostatPrioritySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field ThermostatPrioritySchedule (IB_Schedule).'),
        ] = None,
        heat_pump_waste_heat_recovery: Annotated[
            bool | str | None,
            Field(description='Optional HeatPumpWasteHeatRecovery value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatPumpWasteHeatRecovery.'),
        ] = None,
        equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode: Annotated[
            float | None,
            Field(description='Optional EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode.'),
        ] = None,
        vertical_heightusedfor_piping_correction_factor: Annotated[
            float | None,
            Field(description='Optional VerticalHeightusedforPipingCorrectionFactor value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field VerticalHeightusedforPipingCorrectionFactor.'),
        ] = None,
        piping_correction_factorfor_lengthin_cooling_mode_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PipingCorrectionFactorforLengthinCoolingModeCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforLengthinCoolingModeCurve (IB_Curve).'),
        ] = None,
        piping_correction_factorfor_heightin_cooling_mode_coefficient: Annotated[
            float | None,
            Field(description='Optional PipingCorrectionFactorforHeightinCoolingModeCoefficient value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforHeightinCoolingModeCoefficient.'),
        ] = None,
        equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode: Annotated[
            float | None,
            Field(description='Optional EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode.'),
        ] = None,
        piping_correction_factorfor_lengthin_heating_mode_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PipingCorrectionFactorforLengthinHeatingModeCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforLengthinHeatingModeCurve (IB_Curve).'),
        ] = None,
        piping_correction_factorfor_heightin_heating_mode_coefficient: Annotated[
            float | None,
            Field(description='Optional PipingCorrectionFactorforHeightinHeatingModeCoefficient value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforHeightinHeatingModeCoefficient.'),
        ] = None,
        crankcase_heater_powerper_compressor: Annotated[
            float | None,
            Field(description='Optional CrankcaseHeaterPowerperCompressor value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CrankcaseHeaterPowerperCompressor.'),
        ] = None,
        numberof_compressors: Annotated[
            int | None,
            Field(description='Optional NumberofCompressors value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field NumberofCompressors.'),
        ] = None,
        ratioof_compressor_sizeto_total_compressor_capacity: Annotated[
            float | None,
            Field(description='Optional RatioofCompressorSizetoTotalCompressorCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field RatioofCompressorSizetoTotalCompressorCapacity.'),
        ] = None,
        maximum_outdoor_drybulb_temperaturefor_crankcase_heater: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDrybulbTemperatureforCrankcaseHeater value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MaximumOutdoorDrybulbTemperatureforCrankcaseHeater.'),
        ] = None,
        defrost_strategy: Annotated[
            str | None,
            Field(description='Optional DefrostStrategy value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field DefrostStrategy.'),
        ] = None,
        defrost_control: Annotated[
            str | None,
            Field(description='Optional DefrostControl value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field DefrostControl.'),
        ] = None,
        defrost_energy_input_ratio_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for DefrostEnergyInputRatioModifierFunctionofTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field DefrostEnergyInputRatioModifierFunctionofTemperatureCurve (IB_Curve).'),
        ] = None,
        defrost_time_period_fraction: Annotated[
            float | None,
            Field(description='Optional DefrostTimePeriodFraction value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field DefrostTimePeriodFraction.'),
        ] = None,
        resistive_defrost_heater_capacity: Annotated[
            float | str | None,
            Field(description='Optional ResistiveDefrostHeaterCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field ResistiveDefrostHeaterCapacity.'),
        ] = None,
        maximum_outdoor_drybulb_temperaturefor_defrost_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDrybulbTemperatureforDefrostOperation value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MaximumOutdoorDrybulbTemperatureforDefrostOperation.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Optional CondenserType value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field CondenserType.'),
        ] = None,
        water_condenser_volume_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional WaterCondenserVolumeFlowRate value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field WaterCondenserVolumeFlowRate.'),
        ] = None,
        evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Optional EvaporativeCondenserEffectiveness value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field EvaporativeCondenserEffectiveness.'),
        ] = None,
        evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional EvaporativeCondenserAirFlowRate value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field EvaporativeCondenserAirFlowRate.'),
        ] = None,
        evaporative_condenser_pump_rated_power_consumption: Annotated[
            float | str | None,
            Field(description='Optional EvaporativeCondenserPumpRatedPowerConsumption value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field EvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field BasinHeaterSetpointTemperature.'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional FuelType value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field FuelType.'),
        ] = None,
        minimum_outdoor_temperaturein_heat_recovery_mode: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorTemperatureinHeatRecoveryMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MinimumOutdoorTemperatureinHeatRecoveryMode.'),
        ] = None,
        maximum_outdoor_temperaturein_heat_recovery_mode: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorTemperatureinHeatRecoveryMode value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field MaximumOutdoorTemperatureinHeatRecoveryMode.'),
        ] = None,
        heat_recovery_cooling_capacity_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatRecoveryCoolingCapacityModifierCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingCapacityModifierCurve (IB_Curve).'),
        ] = None,
        initial_heat_recovery_cooling_capacity_fraction: Annotated[
            float | None,
            Field(description='Optional InitialHeatRecoveryCoolingCapacityFraction value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field InitialHeatRecoveryCoolingCapacityFraction.'),
        ] = None,
        heat_recovery_cooling_capacity_time_constant: Annotated[
            float | None,
            Field(description='Optional HeatRecoveryCoolingCapacityTimeConstant value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingCapacityTimeConstant.'),
        ] = None,
        heat_recovery_cooling_energy_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatRecoveryCoolingEnergyModifierCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingEnergyModifierCurve (IB_Curve).'),
        ] = None,
        initial_heat_recovery_cooling_energy_fraction: Annotated[
            float | None,
            Field(description='Optional InitialHeatRecoveryCoolingEnergyFraction value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field InitialHeatRecoveryCoolingEnergyFraction.'),
        ] = None,
        heat_recovery_cooling_energy_time_constant: Annotated[
            float | None,
            Field(description='Optional HeatRecoveryCoolingEnergyTimeConstant value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingEnergyTimeConstant.'),
        ] = None,
        heat_recovery_heating_capacity_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatRecoveryHeatingCapacityModifierCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingCapacityModifierCurve (IB_Curve).'),
        ] = None,
        initial_heat_recovery_heating_capacity_fraction: Annotated[
            float | None,
            Field(description='Optional InitialHeatRecoveryHeatingCapacityFraction value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field InitialHeatRecoveryHeatingCapacityFraction.'),
        ] = None,
        heat_recovery_heating_capacity_time_constant: Annotated[
            float | None,
            Field(description='Optional HeatRecoveryHeatingCapacityTimeConstant value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingCapacityTimeConstant.'),
        ] = None,
        heat_recovery_heating_energy_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatRecoveryHeatingEnergyModifierCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingEnergyModifierCurve (IB_Curve).'),
        ] = None,
        initial_heat_recovery_heating_energy_fraction: Annotated[
            float | None,
            Field(description='Optional InitialHeatRecoveryHeatingEnergyFraction value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field InitialHeatRecoveryHeatingEnergyFraction.'),
        ] = None,
        heat_recovery_heating_energy_time_constant: Annotated[
            float | None,
            Field(description='Optional HeatRecoveryHeatingEnergyTimeConstant value; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingEnergyTimeConstant.'),
        ] = None,
        terminals_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_ZoneHVACTerminalUnitVariableRefrigerantFlow identifiers for IB_AirConditionerVariableRefrigerantFlow.Terminals.'),
        ] = None,
        terminals_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field Name.'),
        ] = None,
        terminals_terminal_unit_availabilityschedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for TerminalUnitAvailabilityschedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child IB_ZoneHVACTerminalUnitVariableRefrigerantFlow field TerminalUnitAvailabilityschedule.'),
        ] = None,
        terminals_supply_air_flow_rate_during_cooling_operation_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline SupplyAirFlowRateDuringCoolingOperation value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        terminals_supply_air_flow_rate_when_no_coolingis_needed_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline SupplyAirFlowRateWhenNoCoolingisNeeded value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field SupplyAirFlowRateWhenNoCoolingisNeeded.'),
        ] = None,
        terminals_supply_air_flow_rate_during_heating_operation_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline SupplyAirFlowRateDuringHeatingOperation value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        terminals_supply_air_flow_rate_when_no_heatingis_needed_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline SupplyAirFlowRateWhenNoHeatingisNeeded value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field SupplyAirFlowRateWhenNoHeatingisNeeded.'),
        ] = None,
        terminals_outdoor_air_flow_rate_during_cooling_operation_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline OutdoorAirFlowRateDuringCoolingOperation value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field OutdoorAirFlowRateDuringCoolingOperation.'),
        ] = None,
        terminals_outdoor_air_flow_rate_during_heating_operation_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline OutdoorAirFlowRateDuringHeatingOperation value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field OutdoorAirFlowRateDuringHeatingOperation.'),
        ] = None,
        terminals_outdoor_air_flow_rate_when_no_coolingor_heatingis_needed_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        terminals_supply_air_fan_operating_mode_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for SupplyAirFanOperatingModeSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child IB_ZoneHVACTerminalUnitVariableRefrigerantFlow field SupplyAirFanOperatingModeSchedule.'),
        ] = None,
        terminals_zone_terminal_unit_on_parasitic_electric_energy_use_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline ZoneTerminalUnitOnParasiticElectricEnergyUse value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field ZoneTerminalUnitOnParasiticElectricEnergyUse.'),
        ] = None,
        terminals_zone_terminal_unit_off_parasitic_electric_energy_use_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline ZoneTerminalUnitOffParasiticElectricEnergyUse value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field ZoneTerminalUnitOffParasiticElectricEnergyUse.'),
        ] = None,
        terminals_rated_total_heating_capacity_sizing_ratio_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedTotalHeatingCapacitySizingRatio value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field RatedTotalHeatingCapacitySizingRatio.'),
        ] = None,
        terminals_maximum_supply_air_temperaturefrom_supplemental_heater_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline MaximumSupplyAirTemperaturefromSupplementalHeater value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field MaximumSupplyAirTemperaturefromSupplementalHeater.'),
        ] = None,
        terminals_maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation.'),
        ] = None,
        terminals_supply_air_fan_placement_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline SupplyAirFanPlacement value for IB_ZoneHVACTerminalUnitVariableRefrigerantFlow; maps to Ironbug IB_AirConditionerVariableRefrigerantFlow.Terminals child field SupplyAirFanPlacement.'),
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
        """Create IB_AirConditionerVariableRefrigerantFlow as a reviewed Ironbug Loops / VRF authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_cooling_cop is not None:
            source_fields['RatedCoolingCOP'] = rated_cooling_cop
        if rated_heating_cop is not None:
            source_fields['RatedHeatingCOP'] = rated_heating_cop
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if cooling_capacity_ratio_boundary_curve_target is not None:
            source_field_targets['CoolingCapacityRatioBoundaryCurve'] = cooling_capacity_ratio_boundary_curve_target
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if gross_rated_total_cooling_capacity is not None:
            source_fields['GrossRatedTotalCoolingCapacity'] = gross_rated_total_cooling_capacity
        if gross_rated_cooling_cop is not None:
            source_fields['GrossRatedCoolingCOP'] = gross_rated_cooling_cop
        if rated_total_cooling_capacity is not None:
            source_fields['RatedTotalCoolingCapacity'] = rated_total_cooling_capacity
        if minimum_outdoor_temperaturein_cooling_mode is not None:
            source_fields['MinimumOutdoorTemperatureinCoolingMode'] = minimum_outdoor_temperaturein_cooling_mode
        if maximum_outdoor_temperaturein_cooling_mode is not None:
            source_fields['MaximumOutdoorTemperatureinCoolingMode'] = maximum_outdoor_temperaturein_cooling_mode
        if cooling_capacity_ratio_modifier_functionof_low_temperature_curve_target is not None:
            source_field_targets['CoolingCapacityRatioModifierFunctionofLowTemperatureCurve'] = cooling_capacity_ratio_modifier_functionof_low_temperature_curve_target
        if cooling_capacity_ratio_modifier_functionof_high_temperature_curve_target is not None:
            source_field_targets['CoolingCapacityRatioModifierFunctionofHighTemperatureCurve'] = cooling_capacity_ratio_modifier_functionof_high_temperature_curve_target
        if cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_target is not None:
            source_field_targets['CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve'] = cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_target
        if cooling_energy_input_ratio_boundary_curve_target is not None:
            source_field_targets['CoolingEnergyInputRatioBoundaryCurve'] = cooling_energy_input_ratio_boundary_curve_target
        if cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_target is not None:
            source_field_targets['CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve'] = cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_target
        if cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target is not None:
            source_field_targets['CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve'] = cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target
        if cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target is not None:
            source_field_targets['CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve'] = cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target
        if cooling_combination_ratio_correction_factor_curve_target is not None:
            source_field_targets['CoolingCombinationRatioCorrectionFactorCurve'] = cooling_combination_ratio_correction_factor_curve_target
        if cooling_part_load_fraction_correlation_curve_target is not None:
            source_field_targets['CoolingPartLoadFractionCorrelationCurve'] = cooling_part_load_fraction_correlation_curve_target
        if gross_rated_heating_capacity is not None:
            source_fields['GrossRatedHeatingCapacity'] = gross_rated_heating_capacity
        if rated_heating_capacity_sizing_ratio is not None:
            source_fields['RatedHeatingCapacitySizingRatio'] = rated_heating_capacity_sizing_ratio
        if rated_total_heating_capacity is not None:
            source_fields['RatedTotalHeatingCapacity'] = rated_total_heating_capacity
        if rated_total_heating_capacity_sizing_ratio is not None:
            source_fields['RatedTotalHeatingCapacitySizingRatio'] = rated_total_heating_capacity_sizing_ratio
        if minimum_outdoor_temperaturein_heating_mode is not None:
            source_fields['MinimumOutdoorTemperatureinHeatingMode'] = minimum_outdoor_temperaturein_heating_mode
        if maximum_outdoor_temperaturein_heating_mode is not None:
            source_fields['MaximumOutdoorTemperatureinHeatingMode'] = maximum_outdoor_temperaturein_heating_mode
        if heating_capacity_ratio_modifier_functionof_low_temperature_curve_target is not None:
            source_field_targets['HeatingCapacityRatioModifierFunctionofLowTemperatureCurve'] = heating_capacity_ratio_modifier_functionof_low_temperature_curve_target
        if heating_capacity_ratio_boundary_curve_target is not None:
            source_field_targets['HeatingCapacityRatioBoundaryCurve'] = heating_capacity_ratio_boundary_curve_target
        if heating_capacity_ratio_modifier_functionof_high_temperature_curve_target is not None:
            source_field_targets['HeatingCapacityRatioModifierFunctionofHighTemperatureCurve'] = heating_capacity_ratio_modifier_functionof_high_temperature_curve_target
        if heating_energy_input_ratio_modifier_functionof_low_temperature_curve_target is not None:
            source_field_targets['HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve'] = heating_energy_input_ratio_modifier_functionof_low_temperature_curve_target
        if heating_energy_input_ratio_boundary_curve_target is not None:
            source_field_targets['HeatingEnergyInputRatioBoundaryCurve'] = heating_energy_input_ratio_boundary_curve_target
        if heating_energy_input_ratio_modifier_functionof_high_temperature_curve_target is not None:
            source_field_targets['HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve'] = heating_energy_input_ratio_modifier_functionof_high_temperature_curve_target
        if heating_performance_curve_outdoor_temperature_type_target is not None:
            source_field_targets['HeatingPerformanceCurveOutdoorTemperatureType'] = heating_performance_curve_outdoor_temperature_type_target
        if heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target is not None:
            source_field_targets['HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve'] = heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_target
        if heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target is not None:
            source_field_targets['HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve'] = heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_target
        if heating_combination_ratio_correction_factor_curve_target is not None:
            source_field_targets['HeatingCombinationRatioCorrectionFactorCurve'] = heating_combination_ratio_correction_factor_curve_target
        if heating_part_load_fraction_correlation_curve_target is not None:
            source_field_targets['HeatingPartLoadFractionCorrelationCurve'] = heating_part_load_fraction_correlation_curve_target
        if minimum_heat_pump_part_load_ratio is not None:
            source_fields['MinimumHeatPumpPartLoadRatio'] = minimum_heat_pump_part_load_ratio
        if master_thermostat_priority_control_type is not None:
            source_fields['MasterThermostatPriorityControlType'] = master_thermostat_priority_control_type
        if thermostat_priority_schedule_target is not None:
            source_field_targets['ThermostatPrioritySchedule'] = thermostat_priority_schedule_target
        if heat_pump_waste_heat_recovery is not None:
            source_fields['HeatPumpWasteHeatRecovery'] = heat_pump_waste_heat_recovery
        if equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode is not None:
            source_fields['EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode'] = equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode
        if vertical_heightusedfor_piping_correction_factor is not None:
            source_fields['VerticalHeightusedforPipingCorrectionFactor'] = vertical_heightusedfor_piping_correction_factor
        if piping_correction_factorfor_lengthin_cooling_mode_curve_target is not None:
            source_field_targets['PipingCorrectionFactorforLengthinCoolingModeCurve'] = piping_correction_factorfor_lengthin_cooling_mode_curve_target
        if piping_correction_factorfor_heightin_cooling_mode_coefficient is not None:
            source_fields['PipingCorrectionFactorforHeightinCoolingModeCoefficient'] = piping_correction_factorfor_heightin_cooling_mode_coefficient
        if equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode is not None:
            source_fields['EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode'] = equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode
        if piping_correction_factorfor_lengthin_heating_mode_curve_target is not None:
            source_field_targets['PipingCorrectionFactorforLengthinHeatingModeCurve'] = piping_correction_factorfor_lengthin_heating_mode_curve_target
        if piping_correction_factorfor_heightin_heating_mode_coefficient is not None:
            source_fields['PipingCorrectionFactorforHeightinHeatingModeCoefficient'] = piping_correction_factorfor_heightin_heating_mode_coefficient
        if crankcase_heater_powerper_compressor is not None:
            source_fields['CrankcaseHeaterPowerperCompressor'] = crankcase_heater_powerper_compressor
        if numberof_compressors is not None:
            source_fields['NumberofCompressors'] = numberof_compressors
        if ratioof_compressor_sizeto_total_compressor_capacity is not None:
            source_fields['RatioofCompressorSizetoTotalCompressorCapacity'] = ratioof_compressor_sizeto_total_compressor_capacity
        if maximum_outdoor_drybulb_temperaturefor_crankcase_heater is not None:
            source_fields['MaximumOutdoorDrybulbTemperatureforCrankcaseHeater'] = maximum_outdoor_drybulb_temperaturefor_crankcase_heater
        if defrost_strategy is not None:
            source_fields['DefrostStrategy'] = defrost_strategy
        if defrost_control is not None:
            source_fields['DefrostControl'] = defrost_control
        if defrost_energy_input_ratio_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['DefrostEnergyInputRatioModifierFunctionofTemperatureCurve'] = defrost_energy_input_ratio_modifier_functionof_temperature_curve_target
        if defrost_time_period_fraction is not None:
            source_fields['DefrostTimePeriodFraction'] = defrost_time_period_fraction
        if resistive_defrost_heater_capacity is not None:
            source_fields['ResistiveDefrostHeaterCapacity'] = resistive_defrost_heater_capacity
        if maximum_outdoor_drybulb_temperaturefor_defrost_operation is not None:
            source_fields['MaximumOutdoorDrybulbTemperatureforDefrostOperation'] = maximum_outdoor_drybulb_temperaturefor_defrost_operation
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if water_condenser_volume_flow_rate is not None:
            source_fields['WaterCondenserVolumeFlowRate'] = water_condenser_volume_flow_rate
        if evaporative_condenser_effectiveness is not None:
            source_fields['EvaporativeCondenserEffectiveness'] = evaporative_condenser_effectiveness
        if evaporative_condenser_air_flow_rate is not None:
            source_fields['EvaporativeCondenserAirFlowRate'] = evaporative_condenser_air_flow_rate
        if evaporative_condenser_pump_rated_power_consumption is not None:
            source_fields['EvaporativeCondenserPumpRatedPowerConsumption'] = evaporative_condenser_pump_rated_power_consumption
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if minimum_outdoor_temperaturein_heat_recovery_mode is not None:
            source_fields['MinimumOutdoorTemperatureinHeatRecoveryMode'] = minimum_outdoor_temperaturein_heat_recovery_mode
        if maximum_outdoor_temperaturein_heat_recovery_mode is not None:
            source_fields['MaximumOutdoorTemperatureinHeatRecoveryMode'] = maximum_outdoor_temperaturein_heat_recovery_mode
        if heat_recovery_cooling_capacity_modifier_curve_target is not None:
            source_field_targets['HeatRecoveryCoolingCapacityModifierCurve'] = heat_recovery_cooling_capacity_modifier_curve_target
        if initial_heat_recovery_cooling_capacity_fraction is not None:
            source_fields['InitialHeatRecoveryCoolingCapacityFraction'] = initial_heat_recovery_cooling_capacity_fraction
        if heat_recovery_cooling_capacity_time_constant is not None:
            source_fields['HeatRecoveryCoolingCapacityTimeConstant'] = heat_recovery_cooling_capacity_time_constant
        if heat_recovery_cooling_energy_modifier_curve_target is not None:
            source_field_targets['HeatRecoveryCoolingEnergyModifierCurve'] = heat_recovery_cooling_energy_modifier_curve_target
        if initial_heat_recovery_cooling_energy_fraction is not None:
            source_fields['InitialHeatRecoveryCoolingEnergyFraction'] = initial_heat_recovery_cooling_energy_fraction
        if heat_recovery_cooling_energy_time_constant is not None:
            source_fields['HeatRecoveryCoolingEnergyTimeConstant'] = heat_recovery_cooling_energy_time_constant
        if heat_recovery_heating_capacity_modifier_curve_target is not None:
            source_field_targets['HeatRecoveryHeatingCapacityModifierCurve'] = heat_recovery_heating_capacity_modifier_curve_target
        if initial_heat_recovery_heating_capacity_fraction is not None:
            source_fields['InitialHeatRecoveryHeatingCapacityFraction'] = initial_heat_recovery_heating_capacity_fraction
        if heat_recovery_heating_capacity_time_constant is not None:
            source_fields['HeatRecoveryHeatingCapacityTimeConstant'] = heat_recovery_heating_capacity_time_constant
        if heat_recovery_heating_energy_modifier_curve_target is not None:
            source_field_targets['HeatRecoveryHeatingEnergyModifierCurve'] = heat_recovery_heating_energy_modifier_curve_target
        if initial_heat_recovery_heating_energy_fraction is not None:
            source_fields['InitialHeatRecoveryHeatingEnergyFraction'] = initial_heat_recovery_heating_energy_fraction
        if heat_recovery_heating_energy_time_constant is not None:
            source_fields['HeatRecoveryHeatingEnergyTimeConstant'] = heat_recovery_heating_energy_time_constant
        if terminals_targets is not None:
            source_property_targets['Terminals'] = terminals_targets
        inline_terminals_fields: dict[str, Any] = {}
        inline_terminals_field_targets: dict[str, Any] = {}
        if terminals_name_values is not None:
            inline_terminals_fields['Name'] = terminals_name_values
        if terminals_terminal_unit_availabilityschedule_targets is not None:
            inline_terminals_field_targets['TerminalUnitAvailabilityschedule'] = terminals_terminal_unit_availabilityschedule_targets
        if terminals_supply_air_flow_rate_during_cooling_operation_values is not None:
            inline_terminals_fields['SupplyAirFlowRateDuringCoolingOperation'] = terminals_supply_air_flow_rate_during_cooling_operation_values
        if terminals_supply_air_flow_rate_when_no_coolingis_needed_values is not None:
            inline_terminals_fields['SupplyAirFlowRateWhenNoCoolingisNeeded'] = terminals_supply_air_flow_rate_when_no_coolingis_needed_values
        if terminals_supply_air_flow_rate_during_heating_operation_values is not None:
            inline_terminals_fields['SupplyAirFlowRateDuringHeatingOperation'] = terminals_supply_air_flow_rate_during_heating_operation_values
        if terminals_supply_air_flow_rate_when_no_heatingis_needed_values is not None:
            inline_terminals_fields['SupplyAirFlowRateWhenNoHeatingisNeeded'] = terminals_supply_air_flow_rate_when_no_heatingis_needed_values
        if terminals_outdoor_air_flow_rate_during_cooling_operation_values is not None:
            inline_terminals_fields['OutdoorAirFlowRateDuringCoolingOperation'] = terminals_outdoor_air_flow_rate_during_cooling_operation_values
        if terminals_outdoor_air_flow_rate_during_heating_operation_values is not None:
            inline_terminals_fields['OutdoorAirFlowRateDuringHeatingOperation'] = terminals_outdoor_air_flow_rate_during_heating_operation_values
        if terminals_outdoor_air_flow_rate_when_no_coolingor_heatingis_needed_values is not None:
            inline_terminals_fields['OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded'] = terminals_outdoor_air_flow_rate_when_no_coolingor_heatingis_needed_values
        if terminals_supply_air_fan_operating_mode_schedule_targets is not None:
            inline_terminals_field_targets['SupplyAirFanOperatingModeSchedule'] = terminals_supply_air_fan_operating_mode_schedule_targets
        if terminals_zone_terminal_unit_on_parasitic_electric_energy_use_values is not None:
            inline_terminals_fields['ZoneTerminalUnitOnParasiticElectricEnergyUse'] = terminals_zone_terminal_unit_on_parasitic_electric_energy_use_values
        if terminals_zone_terminal_unit_off_parasitic_electric_energy_use_values is not None:
            inline_terminals_fields['ZoneTerminalUnitOffParasiticElectricEnergyUse'] = terminals_zone_terminal_unit_off_parasitic_electric_energy_use_values
        if terminals_rated_total_heating_capacity_sizing_ratio_values is not None:
            inline_terminals_fields['RatedTotalHeatingCapacitySizingRatio'] = terminals_rated_total_heating_capacity_sizing_ratio_values
        if terminals_maximum_supply_air_temperaturefrom_supplemental_heater_values is not None:
            inline_terminals_fields['MaximumSupplyAirTemperaturefromSupplementalHeater'] = terminals_maximum_supply_air_temperaturefrom_supplemental_heater_values
        if terminals_maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation_values is not None:
            inline_terminals_fields['MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation'] = terminals_maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation_values
        if terminals_supply_air_fan_placement_values is not None:
            inline_terminals_fields['SupplyAirFanPlacement'] = terminals_supply_air_fan_placement_values
        if terminals_identifiers is not None or inline_terminals_fields or inline_terminals_field_targets:
            if terminals_targets is not None:
                raise ValueError("Provide either terminals_targets or inline terminals_* parameters, not both.")
            inline_source_property_children['Terminals'] = {
                'source_class': 'IB_ZoneHVACTerminalUnitVariableRefrigerantFlow',
                'is_list': True,
                'identifiers': terminals_identifiers,
                'source_fields': inline_terminals_fields,
                'source_field_targets': inline_terminals_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirConditionerVariableRefrigerantFlow',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
