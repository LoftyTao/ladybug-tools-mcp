'MCP tool for detailed_hvac_heat_pump_plant_loop_eir_heating.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_heat_pump_plant_loop_eir_heating tool.'

    @mcp.tool(
        name='heat_pump_plant_loop_eir_heating',
        description=(
            'Create an Ironbug IB_HeatPumpPlantLoopEIRHeating object for EnergyPlus/OpenStudio HeatPump:PlantLoop:EIR:Heating. Use this EIR plant-loop heat pump for the heating side of a reversible plant heat-pump pair, with WaterSource or AirSource condenser type, optional defrost controls, and optional companion cooling object. This is heat-pump plant equipment, not a hydronic Pump:* object. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'heat-pump',
            'heating',
            'plant-loop',
            'plant-component',
            'hot-water',
            'condenser-water',
            'heat-recovery',
            'defrost',
            'curve',
            'control',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_heat_pump_plant_loop_eir_heating(
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
            Field(description="Stable DetailedHVAC object identifier for this plant-loop EIR heating heat pump."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description="Optional EnergyPlus condenser type, usually WaterSource or AirSource; WaterSource is the EnergyPlus default."),
        ] = None,
        load_side_reference_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional load-side reference flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        source_side_reference_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional source-side reference flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        heat_recovery_reference_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional heat-recovery reference flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        reference_capacity: Annotated[
            float | str | None,
            Field(description="Optional reference heating capacity in W, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        reference_coefficientof_performance: Annotated[
            float | None,
            Field(description="Optional reference heating COP in W/W."),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description="Optional sizing multiplier for autosized heating capacity and load-side reference flow."),
        ] = None,
        capacity_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating capacity temperature modifier."),
        ] = None,
        electric_inputto_output_ratio_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for EIR temperature modifier; EIR is 1/COP."),
        ] = None,
        electric_inputto_output_ratio_modifier_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for EIR part-load-ratio modifier."),
        ] = None,
        heating_to_cooling_capacity_sizing_ratio: Annotated[
            float | None,
            Field(description="Optional heating-to-cooling capacity sizing ratio when a companion cooling heat pump is used."),
        ] = None,
        heat_pump_sizing_method: Annotated[
            str | None,
            Field(description="Optional companion sizing method, such as CoolingCapacity, HeatingCapacity, or GreaterOfHeatingOrCooling."),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description="Optional EnergyPlus heat-pump control type, usually Setpoint or Load."),
        ] = None,
        flow_mode: Annotated[
            str | None,
            Field(description="Optional plant-loop flow mode, usually ConstantFlow or VariableSpeedPumping."),
        ] = None,
        minimum_part_load_ratio: Annotated[
            float | None,
            Field(description="Optional minimum part-load ratio before compressor cycling begins."),
        ] = None,
        minimum_source_inlet_temperature: Annotated[
            float | None,
            Field(description="Optional minimum source inlet temperature in C; the heat pump is disabled below this limit."),
        ] = None,
        maximum_source_inlet_temperature: Annotated[
            float | None,
            Field(description="Optional maximum source inlet temperature in C; the heat pump is disabled above this limit."),
        ] = None,
        minimum_supply_water_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for minimum leaving hot-water temperature as a function of outdoor dry-bulb temperature."),
        ] = None,
        maximum_supply_water_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for maximum leaving hot-water temperature as a function of outdoor dry-bulb temperature."),
        ] = None,
        dry_outdoor_correction_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for dry outdoor correction during heating operation."),
        ] = None,
        maximum_outdoor_dry_bulb_temperature_for_defrost_operation: Annotated[
            float | None,
            Field(description="Optional outdoor dry-bulb temperature in C above which defrost operation is inactive."),
        ] = None,
        heat_pump_defrost_control: Annotated[
            str | None,
            Field(description="Optional defrost control choice, such as None, Timed, OnDemand, or TimedEmpirical."),
        ] = None,
        heat_pump_defrost_time_period_fraction: Annotated[
            float | None,
            Field(description="Optional fraction of time in defrost mode, used with timed defrost strategies."),
        ] = None,
        defrost_energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for defrost EIR temperature modifier."),
        ] = None,
        timed_empirical_defrost_frequency_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for timed empirical defrost frequency."),
        ] = None,
        timed_empirical_defrost_heat_load_penalty_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for timed empirical defrost heat-load penalty."),
        ] = None,
        timed_empirical_defrost_heat_input_energy_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for timed empirical defrost heat-input energy fraction."),
        ] = None,
        minimum_heat_recovery_outlet_temperature: Annotated[
            float | None,
            Field(description="Optional minimum heat-recovery leaving water temperature in C; EnergyPlus does not use this with WaterSource condenser type."),
        ] = None,
        heat_recovery_capacity_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heat-recovery heating capacity temperature modifier."),
        ] = None,
        heat_recovery_electric_inputto_output_ratio_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heat-recovery EIR temperature modifier."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional EnergyPlus object name; defaults to the identifier when omitted."),
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
        companion_cooling_heat_pump_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_HeatPumpPlantLoopEIRCooling target or same-model identifier for the companion cooling mode of the same reversible plant-loop heat pump."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_HeatPumpPlantLoopEIRHeating as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        child_targets = [
            companion_cooling_heat_pump_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if load_side_reference_flow_rate is not None:
            source_fields['LoadSideReferenceFlowRate'] = load_side_reference_flow_rate
        if source_side_reference_flow_rate is not None:
            source_fields['SourceSideReferenceFlowRate'] = source_side_reference_flow_rate
        if heat_recovery_reference_flow_rate is not None:
            source_fields['HeatRecoveryReferenceFlowRate'] = heat_recovery_reference_flow_rate
        if reference_capacity is not None:
            source_fields['ReferenceCapacity'] = reference_capacity
        if reference_coefficientof_performance is not None:
            source_fields['ReferenceCoefficientofPerformance'] = reference_coefficientof_performance
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        if capacity_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['CapacityModifierFunctionofTemperatureCurve'] = capacity_modifier_functionof_temperature_curve_target
        if electric_inputto_output_ratio_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['ElectricInputtoOutputRatioModifierFunctionofTemperatureCurve'] = electric_inputto_output_ratio_modifier_functionof_temperature_curve_target
        if electric_inputto_output_ratio_modifier_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['ElectricInputtoOutputRatioModifierFunctionofPartLoadRatioCurve'] = electric_inputto_output_ratio_modifier_functionof_part_load_ratio_curve_target
        if heating_to_cooling_capacity_sizing_ratio is not None:
            source_fields['HeatingToCoolingCapacitySizingRatio'] = heating_to_cooling_capacity_sizing_ratio
        if heat_pump_sizing_method is not None:
            source_fields['HeatPumpSizingMethod'] = heat_pump_sizing_method
        if control_type is not None:
            source_fields['ControlType'] = control_type
        if flow_mode is not None:
            source_fields['FlowMode'] = flow_mode
        if minimum_part_load_ratio is not None:
            source_fields['MinimumPartLoadRatio'] = minimum_part_load_ratio
        if minimum_source_inlet_temperature is not None:
            source_fields['MinimumSourceInletTemperature'] = minimum_source_inlet_temperature
        if maximum_source_inlet_temperature is not None:
            source_fields['MaximumSourceInletTemperature'] = maximum_source_inlet_temperature
        if minimum_supply_water_temperature_curve_target is not None:
            source_field_targets['MinimumSupplyWaterTemperatureCurve'] = minimum_supply_water_temperature_curve_target
        if maximum_supply_water_temperature_curve_target is not None:
            source_field_targets['MaximumSupplyWaterTemperatureCurve'] = maximum_supply_water_temperature_curve_target
        if dry_outdoor_correction_factor_curve_target is not None:
            source_field_targets['DryOutdoorCorrectionFactorCurve'] = dry_outdoor_correction_factor_curve_target
        if maximum_outdoor_dry_bulb_temperature_for_defrost_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureForDefrostOperation'] = maximum_outdoor_dry_bulb_temperature_for_defrost_operation
        if heat_pump_defrost_control is not None:
            source_fields['HeatPumpDefrostControl'] = heat_pump_defrost_control
        if heat_pump_defrost_time_period_fraction is not None:
            source_fields['HeatPumpDefrostTimePeriodFraction'] = heat_pump_defrost_time_period_fraction
        if defrost_energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['DefrostEnergyInputRatioFunctionofTemperatureCurve'] = defrost_energy_input_ratio_functionof_temperature_curve_target
        if timed_empirical_defrost_frequency_curve_target is not None:
            source_field_targets['TimedEmpiricalDefrostFrequencyCurve'] = timed_empirical_defrost_frequency_curve_target
        if timed_empirical_defrost_heat_load_penalty_curve_target is not None:
            source_field_targets['TimedEmpiricalDefrostHeatLoadPenaltyCurve'] = timed_empirical_defrost_heat_load_penalty_curve_target
        if timed_empirical_defrost_heat_input_energy_fraction_curve_target is not None:
            source_field_targets['TimedEmpiricalDefrostHeatInputEnergyFractionCurve'] = timed_empirical_defrost_heat_input_energy_fraction_curve_target
        if minimum_heat_recovery_outlet_temperature is not None:
            source_fields['MinimumHeatRecoveryOutletTemperature'] = minimum_heat_recovery_outlet_temperature
        if heat_recovery_capacity_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['HeatRecoveryCapacityModifierFunctionofTemperatureCurve'] = heat_recovery_capacity_modifier_functionof_temperature_curve_target
        if heat_recovery_electric_inputto_output_ratio_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['HeatRecoveryElectricInputtoOutputRatioModifierFunctionofTemperatureCurve'] = heat_recovery_electric_inputto_output_ratio_modifier_functionof_temperature_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HeatPumpPlantLoopEIRHeating',
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
