'MCP tool for detailed_hvac_coil_performance_dx_cooling.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_performance_dx_cooling tool.'

    @mcp.tool(
        name='coil_performance_dx_cooling',
        description=(
            'Create IB_CoilPerformanceDXCooling, an OpenStudio/EnergyPlus CoilPerformance:DX:Cooling object for one mode or stage of a two-stage DX cooling coil with humidity-control modes. Use the returned target as a normal or enhanced-dehumidification performance child for IB_CoilCoolingDXTwoStageWithHumidityControlMode; use DX cooling coil tools for parent coil equipment. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'coil',
            'cooling',
            'dx',
            'performance',
            'curve',
            'humidity-control',
            'dehumidification',
            'air-loop',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_performance_dx_cooling(
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
            Field(description="Stable identifier for the new IB_CoilPerformanceDXCooling object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        gross_rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Gross total cooling capacity for this DX performance mode at rated conditions. Maps to Ironbug field GrossRatedTotalCoolingCapacity.'),
        ] = None,
        gross_rated_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Gross sensible heat ratio (SHR) for this DX performance mode at rated conditions. Maps to Ironbug field GrossRatedSensibleHeatRatio.'),
        ] = None,
        gross_rated_cooling_cop: Annotated[
            float | None,
            Field(description='Gross cooling coefficient of performance for this DX performance mode. Maps to Ironbug field GrossRatedCoolingCOP.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Rated air volume flow rate across the DX cooling coil for this mode. Maps to Ironbug field RatedAirFlowRate.'),
        ] = None,
        fractionof_air_flow_bypassed_around_coil: Annotated[
            float | None,
            Field(description='Fraction of rated air flow bypassed around the active coil, used for face-split or enhanced dehumidification modes. Maps to Ironbug field FractionofAirFlowBypassedAroundCoil.'),
        ] = None,
        total_cooling_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for total cooling capacity as a function of entering-air and condenser conditions. Maps to Ironbug field TotalCoolingCapacityFunctionofTemperatureCurve.'),
        ] = None,
        total_cooling_capacity_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for total cooling capacity as a function of air-flow fraction. Maps to Ironbug field TotalCoolingCapacityFunctionofFlowFractionCurve.'),
        ] = None,
        energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for energy input ratio (EIR) as a function of entering-air and condenser conditions. Maps to Ironbug field EnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        energy_input_ratio_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for energy input ratio (EIR) as a function of air-flow fraction. Maps to Ironbug field EnergyInputRatioFunctionofFlowFractionCurve.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for part-load fraction and compressor cycling efficiency. Maps to Ironbug field PartLoadFractionCorrelationCurve.'),
        ] = None,
        nominal_timefor_condensate_removalto_begin: Annotated[
            float | None,
            Field(description='Seconds after startup before condensate begins to leave the coil drain, used by the latent degradation model. Maps to Ironbug field NominalTimeforCondensateRemovaltoBegin.'),
        ] = None,
        ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity: Annotated[
            float | None,
            Field(description='Ratio of initial moisture evaporation rate to steady-state latent capacity for latent degradation. Maps to Ironbug field RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity.'),
        ] = None,
        maximum_cycling_rate: Annotated[
            float | None,
            Field(description='Maximum compressor cycling rate in cycles per hour for latent degradation calculations. Maps to Ironbug field MaximumCyclingRate.'),
        ] = None,
        latent_capacity_time_constant: Annotated[
            float | None,
            Field(description='Time constant for latent capacity to reach steady state after startup. Maps to Ironbug field LatentCapacityTimeConstant.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Outdoor condenser type for this DX cooling performance mode, such as air-cooled or evaporatively cooled. Maps to Ironbug field CondenserType.'),
        ] = None,
        evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Effectiveness of the evaporative condenser media; used when the condenser type is evaporatively cooled. Maps to Ironbug field EvaporativeCondenserEffectiveness.'),
        ] = None,
        evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Air flow rate entering the evaporative condenser. Maps to Ironbug field EvaporativeCondenserAirFlowRate.'),
        ] = None,
        evaporative_condenser_pump_rated_power_consumption: Annotated[
            float | str | None,
            Field(description='Rated power for the evaporative condenser water pump. Maps to Ironbug field EvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        sensible_heat_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for sensible heat ratio (SHR) as a function of temperature. Maps to Ironbug field SensibleHeatRatioFunctionofTemperatureCurve.'),
        ] = None,
        sensible_heat_ratio_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Curve target dict or same-model curve identifier for sensible heat ratio (SHR) as a function of air-flow fraction. Maps to Ironbug field SensibleHeatRatioFunctionofFlowFractionCurve.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Explicit OpenStudio object name for this DX cooling performance object. Maps to Ironbug field Name.'),
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
        """Create IB_CoilPerformanceDXCooling as reviewed DX cooling coil performance data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if gross_rated_total_cooling_capacity is not None:
            source_fields['GrossRatedTotalCoolingCapacity'] = gross_rated_total_cooling_capacity
        if gross_rated_sensible_heat_ratio is not None:
            source_fields['GrossRatedSensibleHeatRatio'] = gross_rated_sensible_heat_ratio
        if gross_rated_cooling_cop is not None:
            source_fields['GrossRatedCoolingCOP'] = gross_rated_cooling_cop
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if fractionof_air_flow_bypassed_around_coil is not None:
            source_fields['FractionofAirFlowBypassedAroundCoil'] = fractionof_air_flow_bypassed_around_coil
        if total_cooling_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['TotalCoolingCapacityFunctionofTemperatureCurve'] = total_cooling_capacity_functionof_temperature_curve_target
        if total_cooling_capacity_functionof_flow_fraction_curve_target is not None:
            source_field_targets['TotalCoolingCapacityFunctionofFlowFractionCurve'] = total_cooling_capacity_functionof_flow_fraction_curve_target
        if energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofTemperatureCurve'] = energy_input_ratio_functionof_temperature_curve_target
        if energy_input_ratio_functionof_flow_fraction_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofFlowFractionCurve'] = energy_input_ratio_functionof_flow_fraction_curve_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if nominal_timefor_condensate_removalto_begin is not None:
            source_fields['NominalTimeforCondensateRemovaltoBegin'] = nominal_timefor_condensate_removalto_begin
        if ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity is not None:
            source_fields['RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity'] = ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity
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
        if sensible_heat_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['SensibleHeatRatioFunctionofTemperatureCurve'] = sensible_heat_ratio_functionof_temperature_curve_target
        if sensible_heat_ratio_functionof_flow_fraction_curve_target is not None:
            source_field_targets['SensibleHeatRatioFunctionofFlowFractionCurve'] = sensible_heat_ratio_functionof_flow_fraction_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilPerformanceDXCooling',
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
