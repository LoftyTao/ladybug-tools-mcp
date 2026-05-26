'MCP tool for detailed_hvac_chiller_electric_eir.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_chiller_electric_eir tool.'

    @mcp.tool(
        name='chiller_electric_eir',
        description=(
            'Create IB_ChillerElectricEIR, an OpenStudio/EnergyPlus electric EIR chiller for chilled-water supply with air-cooled or water-cooled condenser behavior. Use the returned target in chilled-water and, when needed, condenser-water plant-loop branches. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'chiller', 'electric', 'eir', 'cooling', 'chilled-water', 'condenser-water', 'heat-recovery', 'plant-loop', 'plant-component', 'curve', 'hvac', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_chiller_electric_eir(
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
            Field(description="Stable identifier for the new IB_ChillerElectricEIR object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Sets Ironbug field Name for IB_ChillerElectricEIR."
            ),
        ] = None,
        reference_capacity: Annotated[
            float | str | None,
            Field(
                description="Optional reference cooling capacity for the electric EIR chiller; maps to Ironbug IB_ChillerElectricEIR field ReferenceCapacity."
            ),
        ] = None,
        reference_cop: Annotated[
            float | None,
            Field(
                description="Optional reference COP for the electric EIR chiller; maps to Ironbug IB_ChillerElectricEIR field ReferenceCOP."
            ),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(
                description="Optional condenser type, such as AirCooled or WaterCooled; maps to Ironbug IB_ChillerElectricEIR field CondenserType."
            ),
        ] = None,
        reference_leaving_chilled_water_temperature: Annotated[
            float | None,
            Field(
                description="Sets Ironbug field ReferenceLeavingChilledWaterTemperature for IB_ChillerElectricEIR."
            ),
        ] = None,
        reference_entering_condenser_fluid_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceEnteringCondenserFluidTemperature value; maps to Ironbug IB_ChillerElectricEIR field ReferenceEnteringCondenserFluidTemperature.'),
        ] = None,
        reference_chilled_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional ReferenceChilledWaterFlowRate value; maps to Ironbug IB_ChillerElectricEIR field ReferenceChilledWaterFlowRate.'),
        ] = None,
        reference_condenser_fluid_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional ReferenceCondenserFluidFlowRate value; maps to Ironbug IB_ChillerElectricEIR field ReferenceCondenserFluidFlowRate.'),
        ] = None,
        cooling_capacity_function_of_temperature: Annotated[
            str | float | int | bool | None,
            Field(description='Optional cooling-capacity temperature curve value or reference; maps to Ironbug IB_ChillerElectricEIR field CoolingCapacityFunctionOfTemperature.'),
        ] = None,
        electric_input_to_cooling_output_ratio_function_of_temperature: Annotated[
            str | float | int | bool | None,
            Field(description='Optional EIR temperature curve value or reference; maps to Ironbug IB_ChillerElectricEIR field ElectricInputToCoolingOutputRatioFunctionOfTemperature.'),
        ] = None,
        electric_input_to_cooling_output_ratio_function_of_plr: Annotated[
            str | float | int | bool | None,
            Field(description='Optional EIR part-load-ratio curve value or reference; maps to Ironbug IB_ChillerElectricEIR field ElectricInputToCoolingOutputRatioFunctionOfPLR.'),
        ] = None,
        minimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumPartLoadRatio value; maps to Ironbug IB_ChillerElectricEIR field MinimumPartLoadRatio.'),
        ] = None,
        maximum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MaximumPartLoadRatio value; maps to Ironbug IB_ChillerElectricEIR field MaximumPartLoadRatio.'),
        ] = None,
        optimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional OptimumPartLoadRatio value; maps to Ironbug IB_ChillerElectricEIR field OptimumPartLoadRatio.'),
        ] = None,
        minimum_unloading_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumUnloadingRatio value; maps to Ironbug IB_ChillerElectricEIR field MinimumUnloadingRatio.'),
        ] = None,
        condenser_fan_power_ratio: Annotated[
            float | None,
            Field(description='Optional CondenserFanPowerRatio value; maps to Ironbug IB_ChillerElectricEIR field CondenserFanPowerRatio.'),
        ] = None,
        fractionof_compressor_electric_consumption_rejectedby_condenser: Annotated[
            float | None,
            Field(description='Optional FractionofCompressorElectricConsumptionRejectedbyCondenser value; maps to Ironbug IB_ChillerElectricEIR field FractionofCompressorElectricConsumptionRejectedbyCondenser.'),
        ] = None,
        leaving_chilled_water_lower_temperature_limit: Annotated[
            float | None,
            Field(description='Optional LeavingChilledWaterLowerTemperatureLimit value; maps to Ironbug IB_ChillerElectricEIR field LeavingChilledWaterLowerTemperatureLimit.'),
        ] = None,
        chiller_flow_mode: Annotated[
            str | None,
            Field(description='Optional ChillerFlowMode value; maps to Ironbug IB_ChillerElectricEIR field ChillerFlowMode.'),
        ] = None,
        design_heat_recovery_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignHeatRecoveryWaterFlowRate value; maps to Ironbug IB_ChillerElectricEIR field DesignHeatRecoveryWaterFlowRate.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Optional SizingFactor value; maps to Ironbug IB_ChillerElectricEIR field SizingFactor.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_ChillerElectricEIR field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_ChillerElectricEIR field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for basin heater operation; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerElectricEIR field BasinHeaterSchedule.'),
        ] = None,
        condenser_heat_recovery_relative_capacity_fraction: Annotated[
            float | None,
            Field(description='Optional CondenserHeatRecoveryRelativeCapacityFraction value; maps to Ironbug IB_ChillerElectricEIR field CondenserHeatRecoveryRelativeCapacityFraction.'),
        ] = None,
        heat_recovery_inlet_high_temperature_limit_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for heat-recovery inlet high-temperature limits; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerElectricEIR field HeatRecoveryInletHighTemperatureLimitSchedule.'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EndUseSubcategory value; maps to Ironbug IB_ChillerElectricEIR field EndUseSubcategory.'),
        ] = None,
        condenser_flow_control: Annotated[
            str | None,
            Field(description='Optional CondenserFlowControl value; maps to Ironbug IB_ChillerElectricEIR field CondenserFlowControl.'),
        ] = None,
        condenser_loop_flow_rate_fraction_functionof_loop_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for condenser-loop flow fraction versus loop part-load ratio; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerElectricEIR field CondenserLoopFlowRateFractionFunctionofLoopPartLoadRatioCurve.'),
        ] = None,
        temperature_difference_across_condenser_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for temperature difference across the condenser; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerElectricEIR field TemperatureDifferenceAcrossCondenserSchedule.'),
        ] = None,
        condenser_minimum_flow_fraction: Annotated[
            float | None,
            Field(description='Optional CondenserMinimumFlowFraction value; maps to Ironbug IB_ChillerElectricEIR field CondenserMinimumFlowFraction.'),
        ] = None,
        thermosiphon_capacity_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for thermosiphon capacity fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerElectricEIR field ThermosiphonCapacityFractionCurve.'),
        ] = None,
        thermosiphon_minimum_temperature_difference: Annotated[
            float | None,
            Field(description='Optional ThermosiphonMinimumTemperatureDifference value; maps to Ironbug IB_ChillerElectricEIR field ThermosiphonMinimumTemperatureDifference.'),
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
        """Create IB_ChillerElectricEIR as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if reference_capacity is not None:
            source_fields['ReferenceCapacity'] = reference_capacity
        if reference_cop is not None:
            source_fields['ReferenceCOP'] = reference_cop
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if reference_leaving_chilled_water_temperature is not None:
            source_fields['ReferenceLeavingChilledWaterTemperature'] = reference_leaving_chilled_water_temperature
        source_properties: dict[str, Any] = {}
        if reference_entering_condenser_fluid_temperature is not None:
            source_fields['ReferenceEnteringCondenserFluidTemperature'] = reference_entering_condenser_fluid_temperature
        if reference_chilled_water_flow_rate is not None:
            source_fields['ReferenceChilledWaterFlowRate'] = reference_chilled_water_flow_rate
        if reference_condenser_fluid_flow_rate is not None:
            source_fields['ReferenceCondenserFluidFlowRate'] = reference_condenser_fluid_flow_rate
        if cooling_capacity_function_of_temperature is not None:
            source_fields['CoolingCapacityFunctionOfTemperature'] = cooling_capacity_function_of_temperature
        if electric_input_to_cooling_output_ratio_function_of_temperature is not None:
            source_fields['ElectricInputToCoolingOutputRatioFunctionOfTemperature'] = electric_input_to_cooling_output_ratio_function_of_temperature
        if electric_input_to_cooling_output_ratio_function_of_plr is not None:
            source_fields['ElectricInputToCoolingOutputRatioFunctionOfPLR'] = electric_input_to_cooling_output_ratio_function_of_plr
        if minimum_part_load_ratio is not None:
            source_fields['MinimumPartLoadRatio'] = minimum_part_load_ratio
        if maximum_part_load_ratio is not None:
            source_fields['MaximumPartLoadRatio'] = maximum_part_load_ratio
        if optimum_part_load_ratio is not None:
            source_fields['OptimumPartLoadRatio'] = optimum_part_load_ratio
        if minimum_unloading_ratio is not None:
            source_fields['MinimumUnloadingRatio'] = minimum_unloading_ratio
        if condenser_fan_power_ratio is not None:
            source_fields['CondenserFanPowerRatio'] = condenser_fan_power_ratio
        if fractionof_compressor_electric_consumption_rejectedby_condenser is not None:
            source_fields['FractionofCompressorElectricConsumptionRejectedbyCondenser'] = fractionof_compressor_electric_consumption_rejectedby_condenser
        if leaving_chilled_water_lower_temperature_limit is not None:
            source_fields['LeavingChilledWaterLowerTemperatureLimit'] = leaving_chilled_water_lower_temperature_limit
        if chiller_flow_mode is not None:
            source_fields['ChillerFlowMode'] = chiller_flow_mode
        if design_heat_recovery_water_flow_rate is not None:
            source_fields['DesignHeatRecoveryWaterFlowRate'] = design_heat_recovery_water_flow_rate
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_schedule_target is not None:
            source_field_targets['BasinHeaterSchedule'] = basin_heater_schedule_target
        if condenser_heat_recovery_relative_capacity_fraction is not None:
            source_fields['CondenserHeatRecoveryRelativeCapacityFraction'] = condenser_heat_recovery_relative_capacity_fraction
        if heat_recovery_inlet_high_temperature_limit_schedule_target is not None:
            source_field_targets['HeatRecoveryInletHighTemperatureLimitSchedule'] = heat_recovery_inlet_high_temperature_limit_schedule_target
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if condenser_flow_control is not None:
            source_fields['CondenserFlowControl'] = condenser_flow_control
        if condenser_loop_flow_rate_fraction_functionof_loop_part_load_ratio_curve_target is not None:
            source_field_targets['CondenserLoopFlowRateFractionFunctionofLoopPartLoadRatioCurve'] = condenser_loop_flow_rate_fraction_functionof_loop_part_load_ratio_curve_target
        if temperature_difference_across_condenser_schedule_target is not None:
            source_field_targets['TemperatureDifferenceAcrossCondenserSchedule'] = temperature_difference_across_condenser_schedule_target
        if condenser_minimum_flow_fraction is not None:
            source_fields['CondenserMinimumFlowFraction'] = condenser_minimum_flow_fraction
        if thermosiphon_capacity_fraction_curve_target is not None:
            source_field_targets['ThermosiphonCapacityFractionCurve'] = thermosiphon_capacity_fraction_curve_target
        if thermosiphon_minimum_temperature_difference is not None:
            source_fields['ThermosiphonMinimumTemperatureDifference'] = thermosiphon_minimum_temperature_difference
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ChillerElectricEIR',
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
