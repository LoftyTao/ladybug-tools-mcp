'MCP tool for detailed_hvac_coil_cooling_dx_multi_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_multi_speed tool.'

    @mcp.tool(
        name='coil_cooling_dx_multi_speed',
        description=(
            'Create IB_CoilCoolingDXMultiSpeed, an OpenStudio/EnergyPlus Coil:Cooling:DX:MultiSpeed object for unitary air-loop and air-to-air heat-pump assemblies. Provide IB_CoilCoolingDXMultiSpeedStageData targets or inline stage fields for the discrete cooling speeds. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'multi-speed', 'air-loop', 'unitary', 'heat-pump', 'stage-data', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_multi_speed(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXMultiSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        stages_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_CoilCoolingDXMultiSpeedStageData targets from detailed_hvac_coil_cooling_dx_multi_speed_stage_data; maps to the Stages child list."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for DX coil availability; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeed field AvailabilitySchedule.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Optional condenser type, commonly AirCooled or EvaporativelyCooled; maps to Ironbug IB_CoilCoolingDXMultiSpeed field CondenserType.'),
        ] = None,
        apply_part_load_fractionto_speeds_greaterthan1: Annotated[
            bool | str | None,
            Field(description='Optional flag controlling whether part-load-fraction losses apply above speed 1; maps to Ironbug IB_CoilCoolingDXMultiSpeed field ApplyPartLoadFractiontoSpeedsGreaterthan1.'),
        ] = None,
        apply_latent_degradationto_speeds_greaterthan1: Annotated[
            bool | str | None,
            Field(description='Optional flag controlling latent-capacity degradation above speed 1; maps to Ironbug IB_CoilCoolingDXMultiSpeed field ApplyLatentDegradationtoSpeedsGreaterthan1.'),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description='Optional crankcase heater capacity in watts; maps to Ironbug IB_CoilCoolingDXMultiSpeed field CrankcaseHeaterCapacity.'),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for crankcase heater capacity versus outdoor temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeed field CrankcaseHeaterCapacityFunctionofTemperatureCurve.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for evaporative-condenser basin heater operation; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXMultiSpeed field BasinHeaterOperatingSchedule.'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional FuelType value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field FuelType.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXMultiSpeed field Name.'),
        ] = None,
        stages_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_CoilCoolingDXMultiSpeedStageData identifiers for IB_CoilCoolingDXMultiSpeed.Stages.'),
        ] = None,
        stages_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field Name.'),
        ] = None,
        stages_gross_rated_total_cooling_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline GrossRatedTotalCoolingCapacity value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field GrossRatedTotalCoolingCapacity.'),
        ] = None,
        stages_gross_rated_sensible_heat_ratio_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline GrossRatedSensibleHeatRatio value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field GrossRatedSensibleHeatRatio.'),
        ] = None,
        stages_gross_rated_cooling_cop_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline GrossRatedCoolingCOP value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field GrossRatedCoolingCOP.'),
        ] = None,
        stages_rated_air_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline RatedAirFlowRate value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedAirFlowRate.'),
        ] = None,
        stages_rated_evaporator_fan_power_per_volume_flow_rate_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedEvaporatorFanPowerPerVolumeFlowRate value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedEvaporatorFanPowerPerVolumeFlowRate.'),
        ] = None,
        stages_rated_evaporator_fan_power_per_volume_flow_rate2017_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedEvaporatorFanPowerPerVolumeFlowRate2017 value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedEvaporatorFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        stages_rated_evaporator_fan_power_per_volume_flow_rate2023_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedEvaporatorFanPowerPerVolumeFlowRate2023 value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedEvaporatorFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        stages_total_cooling_capacity_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed total cooling capacity versus temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field TotalCoolingCapacityFunctionofTemperatureCurve.'),
        ] = None,
        stages_total_cooling_capacity_functionof_flow_fraction_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed total cooling capacity versus air-flow fraction; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field TotalCoolingCapacityFunctionofFlowFractionCurve.'),
        ] = None,
        stages_energy_input_ratio_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed EIR versus temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field EnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        stages_energy_input_ratio_functionof_flow_fraction_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed EIR versus air-flow fraction; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field EnergyInputRatioFunctionofFlowFractionCurve.'),
        ] = None,
        stages_part_load_fraction_correlation_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed part-load-fraction correlation; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field PartLoadFractionCorrelationCurve.'),
        ] = None,
        stages_nominal_timefor_condensate_removalto_begin_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline NominalTimeforCondensateRemovaltoBegin value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field NominalTimeforCondensateRemovaltoBegin.'),
        ] = None,
        stages_ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity.'),
        ] = None,
        stages_maximum_cycling_rate_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumCyclingRate value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field MaximumCyclingRate.'),
        ] = None,
        stages_latent_capacity_time_constant_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline LatentCapacityTimeConstant value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field LatentCapacityTimeConstant.'),
        ] = None,
        stages_rated_waste_heat_fractionof_power_input_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedWasteHeatFractionofPowerInput value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedWasteHeatFractionofPowerInput.'),
        ] = None,
        stages_waste_heat_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for each speed waste-heat fraction versus temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field WasteHeatFunctionofTemperatureCurve.'),
        ] = None,
        stages_evaporative_condenser_effectiveness_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline EvaporativeCondenserEffectiveness value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field EvaporativeCondenserEffectiveness.'),
        ] = None,
        stages_evaporative_condenser_air_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline EvaporativeCondenserAirFlowRate value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field EvaporativeCondenserAirFlowRate.'),
        ] = None,
        stages_rated_evaporative_condenser_pump_power_consumption_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline RatedEvaporativeCondenserPumpPowerConsumption value for IB_CoilCoolingDXMultiSpeedStageData; maps to Ironbug IB_CoilCoolingDXMultiSpeed.Stages child field RatedEvaporativeCondenserPumpPowerConsumption.'),
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
        """Create IB_CoilCoolingDXMultiSpeed as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if apply_part_load_fractionto_speeds_greaterthan1 is not None:
            source_fields['ApplyPartLoadFractiontoSpeedsGreaterthan1'] = apply_part_load_fractionto_speeds_greaterthan1
        if apply_latent_degradationto_speeds_greaterthan1 is not None:
            source_fields['ApplyLatentDegradationtoSpeedsGreaterthan1'] = apply_latent_degradationto_speeds_greaterthan1
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if stages_targets is not None:
            source_property_targets['Stages'] = stages_targets
        inline_stages_fields: dict[str, Any] = {}
        inline_stages_field_targets: dict[str, Any] = {}
        if stages_name_values is not None:
            inline_stages_fields['Name'] = stages_name_values
        if stages_gross_rated_total_cooling_capacity_values is not None:
            inline_stages_fields['GrossRatedTotalCoolingCapacity'] = stages_gross_rated_total_cooling_capacity_values
        if stages_gross_rated_sensible_heat_ratio_values is not None:
            inline_stages_fields['GrossRatedSensibleHeatRatio'] = stages_gross_rated_sensible_heat_ratio_values
        if stages_gross_rated_cooling_cop_values is not None:
            inline_stages_fields['GrossRatedCoolingCOP'] = stages_gross_rated_cooling_cop_values
        if stages_rated_air_flow_rate_values is not None:
            inline_stages_fields['RatedAirFlowRate'] = stages_rated_air_flow_rate_values
        if stages_rated_evaporator_fan_power_per_volume_flow_rate_values is not None:
            inline_stages_fields['RatedEvaporatorFanPowerPerVolumeFlowRate'] = stages_rated_evaporator_fan_power_per_volume_flow_rate_values
        if stages_rated_evaporator_fan_power_per_volume_flow_rate2017_values is not None:
            inline_stages_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2017'] = stages_rated_evaporator_fan_power_per_volume_flow_rate2017_values
        if stages_rated_evaporator_fan_power_per_volume_flow_rate2023_values is not None:
            inline_stages_fields['RatedEvaporatorFanPowerPerVolumeFlowRate2023'] = stages_rated_evaporator_fan_power_per_volume_flow_rate2023_values
        if stages_total_cooling_capacity_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['TotalCoolingCapacityFunctionofTemperatureCurve'] = stages_total_cooling_capacity_functionof_temperature_curve_targets
        if stages_total_cooling_capacity_functionof_flow_fraction_curve_targets is not None:
            inline_stages_field_targets['TotalCoolingCapacityFunctionofFlowFractionCurve'] = stages_total_cooling_capacity_functionof_flow_fraction_curve_targets
        if stages_energy_input_ratio_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['EnergyInputRatioFunctionofTemperatureCurve'] = stages_energy_input_ratio_functionof_temperature_curve_targets
        if stages_energy_input_ratio_functionof_flow_fraction_curve_targets is not None:
            inline_stages_field_targets['EnergyInputRatioFunctionofFlowFractionCurve'] = stages_energy_input_ratio_functionof_flow_fraction_curve_targets
        if stages_part_load_fraction_correlation_curve_targets is not None:
            inline_stages_field_targets['PartLoadFractionCorrelationCurve'] = stages_part_load_fraction_correlation_curve_targets
        if stages_nominal_timefor_condensate_removalto_begin_values is not None:
            inline_stages_fields['NominalTimeforCondensateRemovaltoBegin'] = stages_nominal_timefor_condensate_removalto_begin_values
        if stages_ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity_values is not None:
            inline_stages_fields['RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity'] = stages_ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity_values
        if stages_maximum_cycling_rate_values is not None:
            inline_stages_fields['MaximumCyclingRate'] = stages_maximum_cycling_rate_values
        if stages_latent_capacity_time_constant_values is not None:
            inline_stages_fields['LatentCapacityTimeConstant'] = stages_latent_capacity_time_constant_values
        if stages_rated_waste_heat_fractionof_power_input_values is not None:
            inline_stages_fields['RatedWasteHeatFractionofPowerInput'] = stages_rated_waste_heat_fractionof_power_input_values
        if stages_waste_heat_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['WasteHeatFunctionofTemperatureCurve'] = stages_waste_heat_functionof_temperature_curve_targets
        if stages_evaporative_condenser_effectiveness_values is not None:
            inline_stages_fields['EvaporativeCondenserEffectiveness'] = stages_evaporative_condenser_effectiveness_values
        if stages_evaporative_condenser_air_flow_rate_values is not None:
            inline_stages_fields['EvaporativeCondenserAirFlowRate'] = stages_evaporative_condenser_air_flow_rate_values
        if stages_rated_evaporative_condenser_pump_power_consumption_values is not None:
            inline_stages_fields['RatedEvaporativeCondenserPumpPowerConsumption'] = stages_rated_evaporative_condenser_pump_power_consumption_values
        if stages_identifiers is not None or inline_stages_fields or inline_stages_field_targets:
            if stages_targets is not None:
                raise ValueError("Provide either stages_targets or inline stages_* parameters, not both.")
            inline_source_property_children['Stages'] = {
                'source_class': 'IB_CoilCoolingDXMultiSpeedStageData',
                'is_list': True,
                'identifiers': stages_identifiers,
                'source_fields': inline_stages_fields,
                'source_field_targets': inline_stages_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXMultiSpeed',
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
