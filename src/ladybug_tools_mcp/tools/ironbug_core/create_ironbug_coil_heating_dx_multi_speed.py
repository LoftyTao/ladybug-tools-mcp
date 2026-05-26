'MCP tool for detailed_hvac_coil_heating_dx_multi_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_dx_multi_speed tool.'

    @mcp.tool(
        name='coil_heating_dx_multi_speed',
        description=(
            'Create IB_CoilHeatingDXMultiSpeed, an OpenStudio/EnergyPlus Coil:Heating:DX:MultiSpeed object for multi-speed DX heat-pump heating in unitary air-loop and air-to-air heat-pump assemblies. Provide IB_CoilHeatingDXMultiSpeedStageData targets or inline stage fields for the discrete heating speeds. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'dx', 'multi-speed', 'air-loop', 'unitary', 'heat-pump', 'defrost', 'stage-data', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_dx_multi_speed(
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
            Field(description="Stable identifier for the new IB_CoilHeatingDXMultiSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        stages_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_CoilHeatingDXMultiSpeedStageData targets for the Grasshopper Stages input and source property Stages."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the DX heating coil availability schedule; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field AvailabilitySchedule.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional minimum outdoor dry-bulb temperature where the DX heating compressor can operate. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        outdoor_dry_bulb_temperatureto_turn_on_compressor: Annotated[
            float | None,
            Field(description='Optional outdoor dry-bulb temperature where the compressor turns back on. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field OutdoorDryBulbTemperaturetoTurnOnCompressor.'),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description='Optional crankcase heater capacity in watts. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field CrankcaseHeaterCapacity.'),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for crankcase heater capacity as a function of outdoor temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field CrankcaseHeaterCapacityFunctionofTemperatureCurve.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation: Annotated[
            float | None,
            Field(description='Optional maximum outdoor dry-bulb temperature where the crankcase heater can operate. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation.'),
        ] = None,
        defrost_energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for reverse-cycle defrost energy input ratio as a function of temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field DefrostEnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_defrost_operation: Annotated[
            float | None,
            Field(description='Optional maximum outdoor dry-bulb temperature where defrost operation can occur. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field MaximumOutdoorDryBulbTemperatureforDefrostOperation.'),
        ] = None,
        defrost_strategy: Annotated[
            str | None,
            Field(description='Optional defrost strategy, such as reverse-cycle or resistive. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field DefrostStrategy.'),
        ] = None,
        defrost_control: Annotated[
            str | None,
            Field(description='Optional defrost control mode, such as timed or on-demand. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field DefrostControl.'),
        ] = None,
        defrost_time_period_fraction: Annotated[
            float | None,
            Field(description='Optional fraction of compressor runtime spent in timed defrost. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field DefrostTimePeriodFraction.'),
        ] = None,
        resistive_defrost_heater_capacity: Annotated[
            float | str | None,
            Field(description='Optional resistive defrost heater capacity in watts. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field ResistiveDefrostHeaterCapacity.'),
        ] = None,
        apply_part_load_fractionto_speeds_greaterthan1: Annotated[
            bool | str | None,
            Field(description='Optional flag controlling whether part-load fraction losses apply above speed 1. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field ApplyPartLoadFractiontoSpeedsGreaterthan1.'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional fuel type for the DX heating coil energy input. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field FuelType.'),
        ] = None,
        regionnumberfor_calculating_hspf: Annotated[
            int | None,
            Field(description='Optional HSPF standard-rating region number for the DX heating coil. Maps to Ironbug IB_CoilHeatingDXMultiSpeed field RegionnumberforCalculatingHSPF.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingDXMultiSpeed field Name.'),
        ] = None,
        stages_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_CoilHeatingDXMultiSpeedStageData identifiers for IB_CoilHeatingDXMultiSpeed.Stages.'),
        ] = None,
        stages_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_CoilHeatingDXMultiSpeedStageData; maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field Name.'),
        ] = None,
        stages_gross_rated_heating_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline gross rated heating capacity for each DX heating stage in watts. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field GrossRatedHeatingCapacity.'),
        ] = None,
        stages_gross_rated_heating_cop_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline gross rated COP for each DX heating stage. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field GrossRatedHeatingCOP.'),
        ] = None,
        stages_rated_air_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline rated air flow rate for each DX heating stage. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field RatedAirFlowRate.'),
        ] = None,
        stages_rated_supply_air_fan_power_per_volume_flow_rate_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedSupplyAirFanPowerPerVolumeFlowRate value for IB_CoilHeatingDXMultiSpeedStageData; maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field RatedSupplyAirFanPowerPerVolumeFlowRate.'),
        ] = None,
        stages_rated_supply_air_fan_power_per_volume_flow_rate2017_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedSupplyAirFanPowerPerVolumeFlowRate2017 value for IB_CoilHeatingDXMultiSpeedStageData; maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field RatedSupplyAirFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        stages_rated_supply_air_fan_power_per_volume_flow_rate2023_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedSupplyAirFanPowerPerVolumeFlowRate2023 value for IB_CoilHeatingDXMultiSpeedStageData; maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field RatedSupplyAirFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        stages_heating_capacity_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage heating capacity as a function of temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field HeatingCapacityFunctionofTemperatureCurve.'),
        ] = None,
        stages_heating_capacity_functionof_flow_fraction_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage heating capacity as a function of air flow fraction; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field HeatingCapacityFunctionofFlowFractionCurve.'),
        ] = None,
        stages_energy_input_ratio_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage energy input ratio as a function of temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field EnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        stages_energy_input_ratio_functionof_flow_fraction_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage energy input ratio as a function of air flow fraction; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field EnergyInputRatioFunctionofFlowFractionCurve.'),
        ] = None,
        stages_part_load_fraction_correlation_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage part-load fraction correlation; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field PartLoadFractionCorrelationCurve.'),
        ] = None,
        stages_rated_waste_heat_fractionof_power_input_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedWasteHeatFractionofPowerInput value for IB_CoilHeatingDXMultiSpeedStageData; maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field RatedWasteHeatFractionofPowerInput.'),
        ] = None,
        stages_waste_heat_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline IB_Curve targets for stage recoverable waste heat as a function of temperature; pass target dicts or same-model identifiers. Maps to Ironbug IB_CoilHeatingDXMultiSpeed.Stages child field WasteHeatFunctionofTemperatureCurve.'),
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
        """Create IB_CoilHeatingDXMultiSpeed as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if outdoor_dry_bulb_temperatureto_turn_on_compressor is not None:
            source_fields['OutdoorDryBulbTemperaturetoTurnOnCompressor'] = outdoor_dry_bulb_temperatureto_turn_on_compressor
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation
        if defrost_energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['DefrostEnergyInputRatioFunctionofTemperatureCurve'] = defrost_energy_input_ratio_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperaturefor_defrost_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforDefrostOperation'] = maximum_outdoor_dry_bulb_temperaturefor_defrost_operation
        if defrost_strategy is not None:
            source_fields['DefrostStrategy'] = defrost_strategy
        if defrost_control is not None:
            source_fields['DefrostControl'] = defrost_control
        if defrost_time_period_fraction is not None:
            source_fields['DefrostTimePeriodFraction'] = defrost_time_period_fraction
        if resistive_defrost_heater_capacity is not None:
            source_fields['ResistiveDefrostHeaterCapacity'] = resistive_defrost_heater_capacity
        if apply_part_load_fractionto_speeds_greaterthan1 is not None:
            source_fields['ApplyPartLoadFractiontoSpeedsGreaterthan1'] = apply_part_load_fractionto_speeds_greaterthan1
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if regionnumberfor_calculating_hspf is not None:
            source_fields['RegionnumberforCalculatingHSPF'] = regionnumberfor_calculating_hspf
        if stages_targets is not None:
            source_property_targets['Stages'] = stages_targets
        inline_stages_fields: dict[str, Any] = {}
        inline_stages_field_targets: dict[str, Any] = {}
        if stages_name_values is not None:
            inline_stages_fields['Name'] = stages_name_values
        if stages_gross_rated_heating_capacity_values is not None:
            inline_stages_fields['GrossRatedHeatingCapacity'] = stages_gross_rated_heating_capacity_values
        if stages_gross_rated_heating_cop_values is not None:
            inline_stages_fields['GrossRatedHeatingCOP'] = stages_gross_rated_heating_cop_values
        if stages_rated_air_flow_rate_values is not None:
            inline_stages_fields['RatedAirFlowRate'] = stages_rated_air_flow_rate_values
        if stages_rated_supply_air_fan_power_per_volume_flow_rate_values is not None:
            inline_stages_fields['RatedSupplyAirFanPowerPerVolumeFlowRate'] = stages_rated_supply_air_fan_power_per_volume_flow_rate_values
        if stages_rated_supply_air_fan_power_per_volume_flow_rate2017_values is not None:
            inline_stages_fields['RatedSupplyAirFanPowerPerVolumeFlowRate2017'] = stages_rated_supply_air_fan_power_per_volume_flow_rate2017_values
        if stages_rated_supply_air_fan_power_per_volume_flow_rate2023_values is not None:
            inline_stages_fields['RatedSupplyAirFanPowerPerVolumeFlowRate2023'] = stages_rated_supply_air_fan_power_per_volume_flow_rate2023_values
        if stages_heating_capacity_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['HeatingCapacityFunctionofTemperatureCurve'] = stages_heating_capacity_functionof_temperature_curve_targets
        if stages_heating_capacity_functionof_flow_fraction_curve_targets is not None:
            inline_stages_field_targets['HeatingCapacityFunctionofFlowFractionCurve'] = stages_heating_capacity_functionof_flow_fraction_curve_targets
        if stages_energy_input_ratio_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['EnergyInputRatioFunctionofTemperatureCurve'] = stages_energy_input_ratio_functionof_temperature_curve_targets
        if stages_energy_input_ratio_functionof_flow_fraction_curve_targets is not None:
            inline_stages_field_targets['EnergyInputRatioFunctionofFlowFractionCurve'] = stages_energy_input_ratio_functionof_flow_fraction_curve_targets
        if stages_part_load_fraction_correlation_curve_targets is not None:
            inline_stages_field_targets['PartLoadFractionCorrelationCurve'] = stages_part_load_fraction_correlation_curve_targets
        if stages_rated_waste_heat_fractionof_power_input_values is not None:
            inline_stages_fields['RatedWasteHeatFractionofPowerInput'] = stages_rated_waste_heat_fractionof_power_input_values
        if stages_waste_heat_functionof_temperature_curve_targets is not None:
            inline_stages_field_targets['WasteHeatFunctionofTemperatureCurve'] = stages_waste_heat_functionof_temperature_curve_targets
        if stages_identifiers is not None or inline_stages_fields or inline_stages_field_targets:
            if stages_targets is not None:
                raise ValueError("Provide either stages_targets or inline stages_* parameters, not both.")
            inline_source_property_children['Stages'] = {
                'source_class': 'IB_CoilHeatingDXMultiSpeedStageData',
                'is_list': True,
                'identifiers': stages_identifiers,
                'source_fields': inline_stages_fields,
                'source_field_targets': inline_stages_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingDXMultiSpeed',
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
