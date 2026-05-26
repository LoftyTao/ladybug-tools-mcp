'MCP tool for detailed_hvac_chiller_absorption_indirect.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_chiller_absorption_indirect tool.'

    @mcp.tool(
        name='chiller_absorption_indirect',
        description=(
            'Create IB_ChillerAbsorptionIndirect, an OpenStudio/EnergyPlus indirect absorption chiller for chilled-water supply, condenser-water demand, and optional generator hot-water or steam demand. Use the returned target in plant-loop branches for absorption cooling topology. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'chiller', 'absorption', 'cooling', 'chilled-water', 'condenser-water', 'hot-water', 'plant-loop', 'plant-component', 'curve', 'hvac', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_chiller_absorption_indirect(
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
            Field(description="Stable identifier for the new IB_ChillerAbsorptionIndirect object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(description='Optional absorption chiller nominal cooling capacity; maps to Ironbug IB_ChillerAbsorptionIndirect field NominalCapacity.'),
        ] = None,
        nominal_pumping_power: Annotated[
            float | str | None,
            Field(description='Optional nominal pumping power for the absorption chiller; maps to Ironbug IB_ChillerAbsorptionIndirect field NominalPumpingPower.'),
        ] = None,
        minimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumPartLoadRatio value; maps to Ironbug IB_ChillerAbsorptionIndirect field MinimumPartLoadRatio.'),
        ] = None,
        maximum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MaximumPartLoadRatio value; maps to Ironbug IB_ChillerAbsorptionIndirect field MaximumPartLoadRatio.'),
        ] = None,
        optimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional OptimumPartLoadRatio value; maps to Ironbug IB_ChillerAbsorptionIndirect field OptimumPartLoadRatio.'),
        ] = None,
        design_condenser_inlet_temperature: Annotated[
            float | None,
            Field(description='Optional DesignCondenserInletTemperature value; maps to Ironbug IB_ChillerAbsorptionIndirect field DesignCondenserInletTemperature.'),
        ] = None,
        condenser_inlet_temperature_lower_limit: Annotated[
            float | None,
            Field(description='Optional CondenserInletTemperatureLowerLimit value; maps to Ironbug IB_ChillerAbsorptionIndirect field CondenserInletTemperatureLowerLimit.'),
        ] = None,
        chilled_water_outlet_temperature_lower_limit: Annotated[
            float | None,
            Field(description='Optional ChilledWaterOutletTemperatureLowerLimit value; maps to Ironbug IB_ChillerAbsorptionIndirect field ChilledWaterOutletTemperatureLowerLimit.'),
        ] = None,
        design_chilled_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design chilled-water flow rate; maps to Ironbug IB_ChillerAbsorptionIndirect field DesignChilledWaterFlowRate.'),
        ] = None,
        design_condenser_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design condenser-water flow rate; maps to Ironbug IB_ChillerAbsorptionIndirect field DesignCondenserWaterFlowRate.'),
        ] = None,
        chiller_flow_mode: Annotated[
            str | None,
            Field(description='Optional ChillerFlowMode value; maps to Ironbug IB_ChillerAbsorptionIndirect field ChillerFlowMode.'),
        ] = None,
        generator_heat_input_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for generator heat input versus part-load ratio; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field GeneratorHeatInputFunctionofPartLoadRatioCurve.'),
        ] = None,
        pump_electric_input_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for pump electric input versus part-load ratio; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field PumpElectricInputFunctionofPartLoadRatioCurve.'),
        ] = None,
        capacity_correction_functionof_condenser_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for capacity correction versus condenser temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field CapacityCorrectionFunctionofCondenserTemperatureCurve.'),
        ] = None,
        capacity_correction_functionof_chilled_water_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for capacity correction versus chilled-water temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field CapacityCorrectionFunctionofChilledWaterTemperatureCurve.'),
        ] = None,
        capacity_correction_functionof_generator_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for capacity correction versus generator temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field CapacityCorrectionFunctionofGeneratorTemperatureCurve.'),
        ] = None,
        generator_heat_input_correction_functionof_condenser_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for generator heat input correction versus condenser temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field GeneratorHeatInputCorrectionFunctionofCondenserTemperatureCurve.'),
        ] = None,
        generator_heat_input_correction_functionof_chilled_water_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for generator heat input correction versus chilled-water temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_ChillerAbsorptionIndirect field GeneratorHeatInputCorrectionFunctionofChilledWaterTemperatureCurve.'),
        ] = None,
        generator_heat_source_type: Annotated[
            str | None,
            Field(description='Optional generator heat source type, such as hot-water or steam input; maps to Ironbug IB_ChillerAbsorptionIndirect field GeneratorHeatSourceType.'),
        ] = None,
        design_generator_fluid_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design generator fluid flow rate; maps to Ironbug IB_ChillerAbsorptionIndirect field DesignGeneratorFluidFlowRate.'),
        ] = None,
        temperature_lower_limit_generator_inlet: Annotated[
            float | None,
            Field(description='Optional TemperatureLowerLimitGeneratorInlet value; maps to Ironbug IB_ChillerAbsorptionIndirect field TemperatureLowerLimitGeneratorInlet.'),
        ] = None,
        degreeof_subcoolingin_steam_generator: Annotated[
            float | None,
            Field(description='Optional DegreeofSubcoolinginSteamGenerator value; maps to Ironbug IB_ChillerAbsorptionIndirect field DegreeofSubcoolinginSteamGenerator.'),
        ] = None,
        degreeof_subcoolingin_steam_condensate_loop: Annotated[
            float | None,
            Field(description='Optional DegreeofSubcoolinginSteamCondensateLoop value; maps to Ironbug IB_ChillerAbsorptionIndirect field DegreeofSubcoolinginSteamCondensateLoop.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Optional SizingFactor value; maps to Ironbug IB_ChillerAbsorptionIndirect field SizingFactor.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ChillerAbsorptionIndirect field Name.'),
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
        """Create IB_ChillerAbsorptionIndirect as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if nominal_pumping_power is not None:
            source_fields['NominalPumpingPower'] = nominal_pumping_power
        if minimum_part_load_ratio is not None:
            source_fields['MinimumPartLoadRatio'] = minimum_part_load_ratio
        if maximum_part_load_ratio is not None:
            source_fields['MaximumPartLoadRatio'] = maximum_part_load_ratio
        if optimum_part_load_ratio is not None:
            source_fields['OptimumPartLoadRatio'] = optimum_part_load_ratio
        if design_condenser_inlet_temperature is not None:
            source_fields['DesignCondenserInletTemperature'] = design_condenser_inlet_temperature
        if condenser_inlet_temperature_lower_limit is not None:
            source_fields['CondenserInletTemperatureLowerLimit'] = condenser_inlet_temperature_lower_limit
        if chilled_water_outlet_temperature_lower_limit is not None:
            source_fields['ChilledWaterOutletTemperatureLowerLimit'] = chilled_water_outlet_temperature_lower_limit
        if design_chilled_water_flow_rate is not None:
            source_fields['DesignChilledWaterFlowRate'] = design_chilled_water_flow_rate
        if design_condenser_water_flow_rate is not None:
            source_fields['DesignCondenserWaterFlowRate'] = design_condenser_water_flow_rate
        if chiller_flow_mode is not None:
            source_fields['ChillerFlowMode'] = chiller_flow_mode
        if generator_heat_input_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['GeneratorHeatInputFunctionofPartLoadRatioCurve'] = generator_heat_input_functionof_part_load_ratio_curve_target
        if pump_electric_input_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['PumpElectricInputFunctionofPartLoadRatioCurve'] = pump_electric_input_functionof_part_load_ratio_curve_target
        if capacity_correction_functionof_condenser_temperature_curve_target is not None:
            source_field_targets['CapacityCorrectionFunctionofCondenserTemperatureCurve'] = capacity_correction_functionof_condenser_temperature_curve_target
        if capacity_correction_functionof_chilled_water_temperature_curve_target is not None:
            source_field_targets['CapacityCorrectionFunctionofChilledWaterTemperatureCurve'] = capacity_correction_functionof_chilled_water_temperature_curve_target
        if capacity_correction_functionof_generator_temperature_curve_target is not None:
            source_field_targets['CapacityCorrectionFunctionofGeneratorTemperatureCurve'] = capacity_correction_functionof_generator_temperature_curve_target
        if generator_heat_input_correction_functionof_condenser_temperature_curve_target is not None:
            source_field_targets['GeneratorHeatInputCorrectionFunctionofCondenserTemperatureCurve'] = generator_heat_input_correction_functionof_condenser_temperature_curve_target
        if generator_heat_input_correction_functionof_chilled_water_temperature_curve_target is not None:
            source_field_targets['GeneratorHeatInputCorrectionFunctionofChilledWaterTemperatureCurve'] = generator_heat_input_correction_functionof_chilled_water_temperature_curve_target
        if generator_heat_source_type is not None:
            source_fields['GeneratorHeatSourceType'] = generator_heat_source_type
        if design_generator_fluid_flow_rate is not None:
            source_fields['DesignGeneratorFluidFlowRate'] = design_generator_fluid_flow_rate
        if temperature_lower_limit_generator_inlet is not None:
            source_fields['TemperatureLowerLimitGeneratorInlet'] = temperature_lower_limit_generator_inlet
        if degreeof_subcoolingin_steam_generator is not None:
            source_fields['DegreeofSubcoolinginSteamGenerator'] = degreeof_subcoolingin_steam_generator
        if degreeof_subcoolingin_steam_condensate_loop is not None:
            source_fields['DegreeofSubcoolinginSteamCondensateLoop'] = degreeof_subcoolingin_steam_condensate_loop
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ChillerAbsorptionIndirect',
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
