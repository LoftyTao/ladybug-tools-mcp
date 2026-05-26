'MCP tool for detailed_hvac_coil_cooling_dx_multi_speed_stage_data.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_multi_speed_stage_data tool.'

    @mcp.tool(
        name='coil_cooling_dx_multi_speed_stage_data',
        description=(
            'Create IB_CoilCoolingDXMultiSpeedStageData, the per-speed performance data object used by IB_CoilCoolingDXMultiSpeed. Use the returned target as a stage in detailed_hvac_coil_cooling_dx_multi_speed, or provide equivalent inline stage fields there. This is performance data for a DX cooling coil speed, not a standalone coil or plant-loop object. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'multi-speed', 'stage-data', 'performance', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_multi_speed_stage_data(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXMultiSpeedStageData object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        gross_rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional gross total cooling capacity for this speed in watts or Autosize; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field GrossRatedTotalCoolingCapacity.'),
        ] = None,
        gross_rated_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Optional gross sensible heat ratio for this speed; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field GrossRatedSensibleHeatRatio.'),
        ] = None,
        gross_rated_cooling_cop: Annotated[
            float | None,
            Field(description='Optional gross cooling COP for this speed; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field GrossRatedCoolingCOP.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional rated air flow rate for this speed in m3/s or Autosize; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedAirFlowRate.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate2017 value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedEvaporatorFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate2023 value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedEvaporatorFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        total_cooling_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for total cooling capacity versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field TotalCoolingCapacityFunctionofTemperatureCurve.'),
        ] = None,
        total_cooling_capacity_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for total cooling capacity versus air-flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field TotalCoolingCapacityFunctionofFlowFractionCurve.'),
        ] = None,
        energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for EIR versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field EnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        energy_input_ratio_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for EIR versus air-flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field EnergyInputRatioFunctionofFlowFractionCurve.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for part-load-fraction correlation; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field PartLoadFractionCorrelationCurve.'),
        ] = None,
        nominal_timefor_condensate_removalto_begin: Annotated[
            float | None,
            Field(description='Optional NominalTimeforCondensateRemovaltoBegin value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field NominalTimeforCondensateRemovaltoBegin.'),
        ] = None,
        ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity: Annotated[
            float | None,
            Field(description='Optional RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity.'),
        ] = None,
        maximum_cycling_rate: Annotated[
            float | None,
            Field(description='Optional MaximumCyclingRate value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field MaximumCyclingRate.'),
        ] = None,
        latent_capacity_time_constant: Annotated[
            float | None,
            Field(description='Optional LatentCapacityTimeConstant value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field LatentCapacityTimeConstant.'),
        ] = None,
        rated_waste_heat_fractionof_power_input: Annotated[
            float | None,
            Field(description='Optional RatedWasteHeatFractionofPowerInput value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedWasteHeatFractionofPowerInput.'),
        ] = None,
        waste_heat_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for waste-heat fraction versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field WasteHeatFunctionofTemperatureCurve.'),
        ] = None,
        evaporative_condenser_effectiveness: Annotated[
            float | None,
            Field(description='Optional EvaporativeCondenserEffectiveness value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field EvaporativeCondenserEffectiveness.'),
        ] = None,
        evaporative_condenser_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional EvaporativeCondenserAirFlowRate value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field EvaporativeCondenserAirFlowRate.'),
        ] = None,
        rated_evaporative_condenser_pump_power_consumption: Annotated[
            float | str | None,
            Field(description='Optional RatedEvaporativeCondenserPumpPowerConsumption value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedEvaporativeCondenserPumpPowerConsumption.'),
        ] = None,
        rated_evaporator_fan_power_per_volume_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedEvaporatorFanPowerPerVolumeFlowRate value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field RatedEvaporatorFanPowerPerVolumeFlowRate.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXMultiSpeedStageData field Name.'),
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
        """Create IB_CoilCoolingDXMultiSpeedStageData as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_evaporator_fan_power_per_volume_flow_rate is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate'] = rated_evaporator_fan_power_per_volume_flow_rate
        if gross_rated_total_cooling_capacity is not None:
            source_fields['GrossRatedTotalCoolingCapacity'] = gross_rated_total_cooling_capacity
        if gross_rated_sensible_heat_ratio is not None:
            source_fields['GrossRatedSensibleHeatRatio'] = gross_rated_sensible_heat_ratio
        if gross_rated_cooling_cop is not None:
            source_fields['GrossRatedCoolingCOP'] = gross_rated_cooling_cop
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if rated_evaporator_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2017'] = rated_evaporator_fan_power_per_volume_flow_rate2017
        if rated_evaporator_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2023'] = rated_evaporator_fan_power_per_volume_flow_rate2023
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
        if rated_waste_heat_fractionof_power_input is not None:
            source_fields['RatedWasteHeatFractionofPowerInput'] = rated_waste_heat_fractionof_power_input
        if waste_heat_functionof_temperature_curve_target is not None:
            source_field_targets['WasteHeatFunctionofTemperatureCurve'] = waste_heat_functionof_temperature_curve_target
        if evaporative_condenser_effectiveness is not None:
            source_fields['EvaporativeCondenserEffectiveness'] = evaporative_condenser_effectiveness
        if evaporative_condenser_air_flow_rate is not None:
            source_fields['EvaporativeCondenserAirFlowRate'] = evaporative_condenser_air_flow_rate
        if rated_evaporative_condenser_pump_power_consumption is not None:
            source_fields['RatedEvaporativeCondenserPumpPowerConsumption'] = rated_evaporative_condenser_pump_power_consumption
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXMultiSpeedStageData',
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
