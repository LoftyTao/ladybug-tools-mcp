'MCP tool for detailed_hvac_coil_cooling_dx_two_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_two_speed tool.'

    @mcp.tool(
        name='coil_cooling_dx_two_speed',
        description=(
            'Create IB_CoilCoolingDXTwoSpeed, an OpenStudio/EnergyPlus Coil:Cooling:DX:TwoSpeed object for two-speed DX cooling in unitary air-loop or DX VAV equipment. Use high-speed and low-speed rated fields plus performance curves to describe the compressor/fan states. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'two-speed', 'air-loop', 'unitary', 'vav', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_two_speed(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXTwoSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for two-speed DX coil availability; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field AvailabilitySchedule.'),
        ] = None,
        rated_high_speed_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional high-speed gross total cooling capacity in watts or Autosize; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedTotalCoolingCapacity.'),
        ] = None,
        rated_high_speed_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Optional high-speed gross sensible heat ratio; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedSensibleHeatRatio.'),
        ] = None,
        rated_high_speed_cop: Annotated[
            float | None,
            Field(description='Optional high-speed gross cooling COP; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedCOP.'),
        ] = None,
        rated_high_speed_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional high-speed rated air flow rate in m3/s or Autosize; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedAirFlowRate.'),
        ] = None,
        rated_high_speed_evaporator_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2017 value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_high_speed_evaporator_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2023 value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        total_cooling_capacity_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for high-speed total cooling capacity versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field TotalCoolingCapacityFunctionOfTemperatureCurve.'),
        ] = None,
        total_cooling_capacity_function_of_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for high-speed total cooling capacity versus air-flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field TotalCoolingCapacityFunctionOfFlowFractionCurve.'),
        ] = None,
        energy_input_ratio_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for high-speed EIR versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field EnergyInputRatioFunctionOfTemperatureCurve.'),
        ] = None,
        energy_input_ratio_function_of_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for high-speed EIR versus air-flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field EnergyInputRatioFunctionOfFlowFractionCurve.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for part-load-fraction correlation; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field PartLoadFractionCorrelationCurve.'),
        ] = None,
        rated_low_speed_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional RatedLowSpeedTotalCoolingCapacity value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedTotalCoolingCapacity.'),
        ] = None,
        rated_low_speed_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Optional RatedLowSpeedSensibleHeatRatio value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedSensibleHeatRatio.'),
        ] = None,
        rated_low_speed_cop: Annotated[
            float | None,
            Field(description='Optional RatedLowSpeedCOP value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedCOP.'),
        ] = None,
        rated_low_speed_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional RatedLowSpeedAirFlowRate value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedAirFlowRate.'),
        ] = None,
        rated_low_speed_evaporator_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2017 value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_low_speed_evaporator_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2023 value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        low_speed_total_cooling_capacity_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for low-speed total cooling capacity versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field LowSpeedTotalCoolingCapacityFunctionOfTemperatureCurve.'),
        ] = None,
        low_speed_energy_input_ratio_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for low-speed EIR versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field LowSpeedEnergyInputRatioFunctionOfTemperatureCurve.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Optional condenser type, commonly AirCooled or EvaporativelyCooled; maps to Ironbug IB_CoilCoolingDXTwoSpeed field CondenserType.'),
        ] = None,
        high_speed_evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Optional HighSpeedEvaporativeCondenserEffectiveness value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field HighSpeedEvaporativeCondenserEffectiveness.'),
        ] = None,
        high_speed_evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional HighSpeedEvaporativeCondenserAirFlowRate value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field HighSpeedEvaporativeCondenserAirFlowRate.'),
        ] = None,
        high_speed_evaporative_condenser_pump_rated_power_consumption: Annotated[
            float | str | None,
            Field(description='Optional HighSpeedEvaporativeCondenserPumpRatedPowerConsumption value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field HighSpeedEvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        low_speed_evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Optional LowSpeedEvaporativeCondenserEffectiveness value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field LowSpeedEvaporativeCondenserEffectiveness.'),
        ] = None,
        low_speed_evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional LowSpeedEvaporativeCondenserAirFlowRate value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field LowSpeedEvaporativeCondenserAirFlowRate.'),
        ] = None,
        low_speed_evaporative_condenser_pump_rated_power_consumption: Annotated[
            float | str | None,
            Field(description='Optional LowSpeedEvaporativeCondenserPumpRatedPowerConsumption value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field LowSpeedEvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for evaporative-condenser basin heater operation; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoSpeed field BasinHeaterOperatingSchedule.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        unit_internal_static_air_pressure: Annotated[
            float | None,
            Field(description='Optional UnitInternalStaticAirPressure value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field UnitInternalStaticAirPressure.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXTwoSpeed field Name.'),
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
        """Create IB_CoilCoolingDXTwoSpeed as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_high_speed_total_cooling_capacity is not None:
            source_fields['RatedHighSpeedTotalCoolingCapacity'] = rated_high_speed_total_cooling_capacity
        if rated_high_speed_sensible_heat_ratio is not None:
            source_fields['RatedHighSpeedSensibleHeatRatio'] = rated_high_speed_sensible_heat_ratio
        if rated_high_speed_cop is not None:
            source_fields['RatedHighSpeedCOP'] = rated_high_speed_cop
        if rated_high_speed_air_flow_rate is not None:
            source_fields['RatedHighSpeedAirFlowRate'] = rated_high_speed_air_flow_rate
        if rated_high_speed_evaporator_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2017'] = rated_high_speed_evaporator_fan_power_per_volume_flow_rate2017
        if rated_high_speed_evaporator_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2023'] = rated_high_speed_evaporator_fan_power_per_volume_flow_rate2023
        if total_cooling_capacity_function_of_temperature_curve_target is not None:
            source_field_targets['TotalCoolingCapacityFunctionOfTemperatureCurve'] = total_cooling_capacity_function_of_temperature_curve_target
        if total_cooling_capacity_function_of_flow_fraction_curve_target is not None:
            source_field_targets['TotalCoolingCapacityFunctionOfFlowFractionCurve'] = total_cooling_capacity_function_of_flow_fraction_curve_target
        if energy_input_ratio_function_of_temperature_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionOfTemperatureCurve'] = energy_input_ratio_function_of_temperature_curve_target
        if energy_input_ratio_function_of_flow_fraction_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionOfFlowFractionCurve'] = energy_input_ratio_function_of_flow_fraction_curve_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if rated_low_speed_total_cooling_capacity is not None:
            source_fields['RatedLowSpeedTotalCoolingCapacity'] = rated_low_speed_total_cooling_capacity
        if rated_low_speed_sensible_heat_ratio is not None:
            source_fields['RatedLowSpeedSensibleHeatRatio'] = rated_low_speed_sensible_heat_ratio
        if rated_low_speed_cop is not None:
            source_fields['RatedLowSpeedCOP'] = rated_low_speed_cop
        if rated_low_speed_air_flow_rate is not None:
            source_fields['RatedLowSpeedAirFlowRate'] = rated_low_speed_air_flow_rate
        if rated_low_speed_evaporator_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2017'] = rated_low_speed_evaporator_fan_power_per_volume_flow_rate2017
        if rated_low_speed_evaporator_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2023'] = rated_low_speed_evaporator_fan_power_per_volume_flow_rate2023
        if low_speed_total_cooling_capacity_function_of_temperature_curve_target is not None:
            source_field_targets['LowSpeedTotalCoolingCapacityFunctionOfTemperatureCurve'] = low_speed_total_cooling_capacity_function_of_temperature_curve_target
        if low_speed_energy_input_ratio_function_of_temperature_curve_target is not None:
            source_field_targets['LowSpeedEnergyInputRatioFunctionOfTemperatureCurve'] = low_speed_energy_input_ratio_function_of_temperature_curve_target
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if high_speed_evaporative_condenser_effectiveness is not None:
            source_fields['HighSpeedEvaporativeCondenserEffectiveness'] = high_speed_evaporative_condenser_effectiveness
        if high_speed_evaporative_condenser_air_flow_rate is not None:
            source_fields['HighSpeedEvaporativeCondenserAirFlowRate'] = high_speed_evaporative_condenser_air_flow_rate
        if high_speed_evaporative_condenser_pump_rated_power_consumption is not None:
            source_fields['HighSpeedEvaporativeCondenserPumpRatedPowerConsumption'] = high_speed_evaporative_condenser_pump_rated_power_consumption
        if low_speed_evaporative_condenser_effectiveness is not None:
            source_fields['LowSpeedEvaporativeCondenserEffectiveness'] = low_speed_evaporative_condenser_effectiveness
        if low_speed_evaporative_condenser_air_flow_rate is not None:
            source_fields['LowSpeedEvaporativeCondenserAirFlowRate'] = low_speed_evaporative_condenser_air_flow_rate
        if low_speed_evaporative_condenser_pump_rated_power_consumption is not None:
            source_fields['LowSpeedEvaporativeCondenserPumpRatedPowerConsumption'] = low_speed_evaporative_condenser_pump_rated_power_consumption
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if unit_internal_static_air_pressure is not None:
            source_fields['UnitInternalStaticAirPressure'] = unit_internal_static_air_pressure
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXTwoSpeed',
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
