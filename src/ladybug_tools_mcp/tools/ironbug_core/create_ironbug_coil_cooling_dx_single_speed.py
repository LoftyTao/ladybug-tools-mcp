'MCP tool for detailed_hvac_coil_cooling_dx_single_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_single_speed tool.'

    @mcp.tool(
        name='coil_cooling_dx_single_speed',
        description=(
            'Create IB_CoilCoolingDXSingleSpeed, an Ironbug single-speed direct '
            'expansion (DX) cooling coil component that maps downstream to '
            'EnergyPlus/OpenStudio Coil:Cooling:DX:SingleSpeed. Use the '
            'returned target as the cooling-coil child for PTAC, PTHP, or '
            'unitary air-loop DetailedHVAC assemblies; for PTHP heat-pump '
            'workflows, pair it with a DX heating coil and electric supplemental '
            'heat coil target. This is not a hydronic plant-loop coil and not '
            'a Honeybee Energy HVAC template. Returns '
            'target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'air-loop', 'zone-equipment', 'ptac', 'pthp', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_single_speed(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXSingleSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the DX cooling coil available.'),
        ] = None,
        rated_cop: Annotated[
            float | None,
            Field(description='Optional RatedCOP value in W/W for IB_CoilCoolingDXSingleSpeed.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate2017 value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field RatedEvaporatorFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate2023 value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field RatedEvaporatorFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        total_cooling_capacity_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for TotalCoolingCapacityFunctionOfTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        total_cooling_capacity_function_of_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for TotalCoolingCapacityFunctionOfFlowFractionCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        energy_input_ratio_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for EnergyInputRatioFunctionOfTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        energy_input_ratio_function_of_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for EnergyInputRatioFunctionOfFlowFractionCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for PartLoadFractionCorrelationCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        nominal_time_for_condensate_removal_to_begin: Annotated[
            float | None,
            Field(description='Optional NominalTimeForCondensateRemovalToBegin value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field NominalTimeForCondensateRemovalToBegin.'),
        ] = None,
        ratio_of_initial_moisture_evaporation_rate_and_steady_state_latent_capacity: Annotated[
            float | None,
            Field(description='Optional RatioOfInitialMoistureEvaporationRateAndSteadyStateLatentCapacity value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field RatioOfInitialMoistureEvaporationRateAndSteadyStateLatentCapacity.'),
        ] = None,
        maximum_cycling_rate: Annotated[
            float | None,
            Field(description='Optional MaximumCyclingRate value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field MaximumCyclingRate.'),
        ] = None,
        latent_capacity_time_constant: Annotated[
            float | None,
            Field(description='Optional LatentCapacityTimeConstant value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field LatentCapacityTimeConstant.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Optional CondenserType value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field CondenserType.'),
        ] = None,
        evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Optional EvaporativeCondenserEffectiveness value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field EvaporativeCondenserEffectiveness.'),
        ] = None,
        evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional EvaporativeCondenserAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        evaporative_condenser_pump_rated_power_consumption: Annotated[
            float | str | None,
            Field(description='Optional EvaporativeCondenserPumpRatedPowerConsumption value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field EvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description='Optional CrankcaseHeaterCapacity value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field CrankcaseHeaterCapacity.'),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for CrankcaseHeaterCapacityFunctionofTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperature_for_crankcase_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureForCrankcaseHeaterOperation value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field MaximumOutdoorDryBulbTemperatureForCrankcaseHeaterOperation.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for BasinHeaterOperatingSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional RatedTotalCoolingCapacity in W, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        rated_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Optional RatedSensibleHeatRatio, dimensionless, typically between 0.5 and 1.0, or an accepted autosizable literal.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional RatedAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate in W/(m3/s), or an EnergyPlus autosizable/default literal accepted by Ironbug.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXSingleSpeed field Name.'),
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
        """Create IB_CoilCoolingDXSingleSpeed as a reviewed DX cooling coil."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_evaporator_fan_power_per_volume_flow_rate is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate'] = rated_evaporator_fan_power_per_volume_flow_rate
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_cop is not None:
            source_fields['RatedCOP'] = rated_cop
        if rated_evaporator_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2017'] = rated_evaporator_fan_power_per_volume_flow_rate2017
        if rated_evaporator_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2023'] = rated_evaporator_fan_power_per_volume_flow_rate2023
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
        if nominal_time_for_condensate_removal_to_begin is not None:
            source_fields['NominalTimeForCondensateRemovalToBegin'] = nominal_time_for_condensate_removal_to_begin
        if ratio_of_initial_moisture_evaporation_rate_and_steady_state_latent_capacity is not None:
            source_fields['RatioOfInitialMoistureEvaporationRateAndSteadyStateLatentCapacity'] = ratio_of_initial_moisture_evaporation_rate_and_steady_state_latent_capacity
        if maximum_cycling_rate is not None:
            source_fields['MaximumCyclingRate'] = maximum_cycling_rate
        if latent_capacity_time_constant is not None:
            source_fields['LatentCapacityTimeConstant'] = latent_capacity_time_constant
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if evaporative_condenser_effectiveness is not None:
            source_fields['EvaporativeCondenserEffectiveness'] = evaporative_condenser_effectiveness
        if evaporative_condenser_air_flow_rate is not None:
            source_fields['EvaporativeCondenserAirFlowRate'] = evaporative_condenser_air_flow_rate
        if evaporative_condenser_pump_rated_power_consumption is not None:
            source_fields['EvaporativeCondenserPumpRatedPowerConsumption'] = evaporative_condenser_pump_rated_power_consumption
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperature_for_crankcase_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureForCrankcaseHeaterOperation'] = maximum_outdoor_dry_bulb_temperature_for_crankcase_heater_operation
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if rated_total_cooling_capacity is not None:
            source_fields['RatedTotalCoolingCapacity'] = rated_total_cooling_capacity
        if rated_sensible_heat_ratio is not None:
            source_fields['RatedSensibleHeatRatio'] = rated_sensible_heat_ratio
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXSingleSpeed',
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
