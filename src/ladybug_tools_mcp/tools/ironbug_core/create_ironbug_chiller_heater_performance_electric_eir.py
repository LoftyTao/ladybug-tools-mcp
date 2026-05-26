'MCP tool for detailed_hvac_chiller_heater_performance_electric_eir.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_chiller_heater_performance_electric_eir tool.'

    @mcp.tool(
        name='chiller_heater_performance_electric_eir',
        description=(
            'Create IB_ChillerHeaterPerformanceElectricEIR, the performance data object for a CentralHeatPumpSystem chiller-heater module. Use the returned target with detailed_hvac_central_heat_pump_system_module, then assemble the module into a central heat-pump system. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'chiller-heater', 'heat-pump', 'central-system', 'performance', 'curve', 'heating', 'cooling', 'chilled-water', 'hot-water', 'condenser-water', 'component', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_chiller_heater_performance_electric_eir(
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
            Field(description="Stable identifier for the new IB_ChillerHeaterPerformanceElectricEIR object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        reference_cooling_mode_evaporator_capacity: Annotated[
            float | str | None,
            Field(description='Optional reference evaporator capacity for cooling mode; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceCoolingModeEvaporatorCapacity.'),
        ] = None,
        reference_cooling_mode_cop: Annotated[
            float | None,
            Field(description='Optional reference COP for cooling mode; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceCoolingModeCOP.'),
        ] = None,
        reference_cooling_mode_leaving_chilled_water_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceCoolingModeLeavingChilledWaterTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceCoolingModeLeavingChilledWaterTemperature.'),
        ] = None,
        reference_cooling_mode_entering_condenser_fluid_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceCoolingModeEnteringCondenserFluidTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceCoolingModeEnteringCondenserFluidTemperature.'),
        ] = None,
        reference_cooling_mode_leaving_condenser_water_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceCoolingModeLeavingCondenserWaterTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceCoolingModeLeavingCondenserWaterTemperature.'),
        ] = None,
        reference_heating_mode_cooling_capacity_ratio: Annotated[
            float | None,
            Field(description='Optional heating-mode cooling-capacity ratio for the chiller-heater performance object; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceHeatingModeCoolingCapacityRatio.'),
        ] = None,
        reference_heating_mode_cooling_power_input_ratio: Annotated[
            float | None,
            Field(description='Optional heating-mode cooling-power input ratio for the chiller-heater performance object; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceHeatingModeCoolingPowerInputRatio.'),
        ] = None,
        reference_heating_mode_leaving_chilled_water_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceHeatingModeLeavingChilledWaterTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceHeatingModeLeavingChilledWaterTemperature.'),
        ] = None,
        reference_heating_mode_leaving_condenser_water_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceHeatingModeLeavingCondenserWaterTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceHeatingModeLeavingCondenserWaterTemperature.'),
        ] = None,
        reference_heating_mode_entering_condenser_fluid_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceHeatingModeEnteringCondenserFluidTemperature value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ReferenceHeatingModeEnteringCondenserFluidTemperature.'),
        ] = None,
        heating_mode_entering_chilled_water_temperature_low_limit: Annotated[
            float | None,
            Field(description='Optional HeatingModeEnteringChilledWaterTemperatureLowLimit value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeEnteringChilledWaterTemperatureLowLimit.'),
        ] = None,
        chilled_water_flow_mode_type: Annotated[
            str | None,
            Field(description='Optional ChilledWaterFlowModeType value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field ChilledWaterFlowModeType.'),
        ] = None,
        design_chilled_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignChilledWaterFlowRate value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field DesignChilledWaterFlowRate.'),
        ] = None,
        design_condenser_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignCondenserWaterFlowRate value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field DesignCondenserWaterFlowRate.'),
        ] = None,
        design_hot_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional design hot-water flow rate for the chiller-heater module; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field DesignHotWaterFlowRate.'),
        ] = None,
        compressor_motor_efficiency: Annotated[
            float | None,
            Field(description='Optional CompressorMotorEfficiency value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CompressorMotorEfficiency.'),
        ] = None,
        condenser_type: Annotated[
            str | None,
            Field(description='Optional condenser type for the chiller-heater performance object; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CondenserType.'),
        ] = None,
        cooling_mode_temperature_curve_condenser_water_independent_variable_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for the cooling-mode condenser-water independent variable; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CoolingModeTemperatureCurveCondenserWaterIndependentVariable.'),
        ] = None,
        cooling_mode_cooling_capacity_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for cooling-mode capacity versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CoolingModeCoolingCapacityFunctionOfTemperatureCurve.'),
        ] = None,
        cooling_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for cooling-mode EIR versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CoolingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve.'),
        ] = None,
        cooling_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for cooling-mode EIR versus part-load ratio; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CoolingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve.'),
        ] = None,
        cooling_mode_cooling_capacity_optimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional CoolingModeCoolingCapacityOptimumPartLoadRatio value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field CoolingModeCoolingCapacityOptimumPartLoadRatio.'),
        ] = None,
        heating_mode_temperature_curve_condenser_water_independent_variable_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for the heating-mode condenser-water independent variable; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeTemperatureCurveCondenserWaterIndependentVariable.'),
        ] = None,
        heating_mode_cooling_capacity_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating-mode capacity versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeCoolingCapacityFunctionOfTemperatureCurve.'),
        ] = None,
        heating_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating-mode EIR versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve.'),
        ] = None,
        heating_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating-mode EIR versus part-load ratio; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve.'),
        ] = None,
        heating_mode_cooling_capacity_optimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional HeatingModeCoolingCapacityOptimumPartLoadRatio value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field HeatingModeCoolingCapacityOptimumPartLoadRatio.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Optional SizingFactor value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field SizingFactor.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ChillerHeaterPerformanceElectricEIR field Name.'),
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
        """Create IB_ChillerHeaterPerformanceElectricEIR as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if reference_cooling_mode_evaporator_capacity is not None:
            source_fields['ReferenceCoolingModeEvaporatorCapacity'] = reference_cooling_mode_evaporator_capacity
        if reference_cooling_mode_cop is not None:
            source_fields['ReferenceCoolingModeCOP'] = reference_cooling_mode_cop
        if reference_cooling_mode_leaving_chilled_water_temperature is not None:
            source_fields['ReferenceCoolingModeLeavingChilledWaterTemperature'] = reference_cooling_mode_leaving_chilled_water_temperature
        if reference_cooling_mode_entering_condenser_fluid_temperature is not None:
            source_fields['ReferenceCoolingModeEnteringCondenserFluidTemperature'] = reference_cooling_mode_entering_condenser_fluid_temperature
        if reference_cooling_mode_leaving_condenser_water_temperature is not None:
            source_fields['ReferenceCoolingModeLeavingCondenserWaterTemperature'] = reference_cooling_mode_leaving_condenser_water_temperature
        if reference_heating_mode_cooling_capacity_ratio is not None:
            source_fields['ReferenceHeatingModeCoolingCapacityRatio'] = reference_heating_mode_cooling_capacity_ratio
        if reference_heating_mode_cooling_power_input_ratio is not None:
            source_fields['ReferenceHeatingModeCoolingPowerInputRatio'] = reference_heating_mode_cooling_power_input_ratio
        if reference_heating_mode_leaving_chilled_water_temperature is not None:
            source_fields['ReferenceHeatingModeLeavingChilledWaterTemperature'] = reference_heating_mode_leaving_chilled_water_temperature
        if reference_heating_mode_leaving_condenser_water_temperature is not None:
            source_fields['ReferenceHeatingModeLeavingCondenserWaterTemperature'] = reference_heating_mode_leaving_condenser_water_temperature
        if reference_heating_mode_entering_condenser_fluid_temperature is not None:
            source_fields['ReferenceHeatingModeEnteringCondenserFluidTemperature'] = reference_heating_mode_entering_condenser_fluid_temperature
        if heating_mode_entering_chilled_water_temperature_low_limit is not None:
            source_fields['HeatingModeEnteringChilledWaterTemperatureLowLimit'] = heating_mode_entering_chilled_water_temperature_low_limit
        if chilled_water_flow_mode_type is not None:
            source_fields['ChilledWaterFlowModeType'] = chilled_water_flow_mode_type
        if design_chilled_water_flow_rate is not None:
            source_fields['DesignChilledWaterFlowRate'] = design_chilled_water_flow_rate
        if design_condenser_water_flow_rate is not None:
            source_fields['DesignCondenserWaterFlowRate'] = design_condenser_water_flow_rate
        if design_hot_water_flow_rate is not None:
            source_fields['DesignHotWaterFlowRate'] = design_hot_water_flow_rate
        if compressor_motor_efficiency is not None:
            source_fields['CompressorMotorEfficiency'] = compressor_motor_efficiency
        if condenser_type is not None:
            source_fields['CondenserType'] = condenser_type
        if cooling_mode_temperature_curve_condenser_water_independent_variable_target is not None:
            source_field_targets['CoolingModeTemperatureCurveCondenserWaterIndependentVariable'] = cooling_mode_temperature_curve_condenser_water_independent_variable_target
        if cooling_mode_cooling_capacity_function_of_temperature_curve_target is not None:
            source_field_targets['CoolingModeCoolingCapacityFunctionOfTemperatureCurve'] = cooling_mode_cooling_capacity_function_of_temperature_curve_target
        if cooling_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target is not None:
            source_field_targets['CoolingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve'] = cooling_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target
        if cooling_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target is not None:
            source_field_targets['CoolingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve'] = cooling_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target
        if cooling_mode_cooling_capacity_optimum_part_load_ratio is not None:
            source_fields['CoolingModeCoolingCapacityOptimumPartLoadRatio'] = cooling_mode_cooling_capacity_optimum_part_load_ratio
        if heating_mode_temperature_curve_condenser_water_independent_variable_target is not None:
            source_field_targets['HeatingModeTemperatureCurveCondenserWaterIndependentVariable'] = heating_mode_temperature_curve_condenser_water_independent_variable_target
        if heating_mode_cooling_capacity_function_of_temperature_curve_target is not None:
            source_field_targets['HeatingModeCoolingCapacityFunctionOfTemperatureCurve'] = heating_mode_cooling_capacity_function_of_temperature_curve_target
        if heating_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target is not None:
            source_field_targets['HeatingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve'] = heating_mode_electric_input_to_cooling_output_ratio_function_of_temperature_curve_target
        if heating_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target is not None:
            source_field_targets['HeatingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve'] = heating_mode_electric_input_to_cooling_output_ratio_function_of_part_load_ratio_curve_target
        if heating_mode_cooling_capacity_optimum_part_load_ratio is not None:
            source_fields['HeatingModeCoolingCapacityOptimumPartLoadRatio'] = heating_mode_cooling_capacity_optimum_part_load_ratio
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ChillerHeaterPerformanceElectricEIR',
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
