'MCP tool for detailed_hvac_boiler_hot_water.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_boiler_hot_water tool.'

    @mcp.tool(
        name='boiler_hot_water',
        description=(
            'Create IB_BoilerHotWater, an OpenStudio/EnergyPlus hot-water boiler component for plant-loop supply-side heating. Use the returned target in an IB_PlantLoop branch with hot-water sizing and setpoint control. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'boiler', 'hot-water', 'heating', 'plant-loop', 'plant-component', 'curve', 'hvac', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_boiler_hot_water(
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
            Field(description="Stable identifier for the new IB_BoilerHotWater object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Sets Ironbug field Name for IB_BoilerHotWater."
            ),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(
                description="Optional boiler fuel type; maps to Ironbug IB_BoilerHotWater field FuelType."
            ),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(
                description="Optional nominal boiler heating capacity; maps to Ironbug IB_BoilerHotWater field NominalCapacity."
            ),
        ] = None,
        nominal_thermal_efficiency: Annotated[
            float | None,
            Field(
                description="Optional boiler thermal efficiency fraction; maps to Ironbug IB_BoilerHotWater field NominalThermalEfficiency."
            ),
        ] = None,
        normalized_boiler_efficiency_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_Curve target for the normalized boiler efficiency curve; pass a target dict or same-model identifier. Maps to Ironbug IB_BoilerHotWater field NormalizedBoilerEfficiencyCurve."
            ),
        ] = None,
        efficiency_curve_temperature_evaluation_variable_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for the boiler efficiency-curve temperature evaluation variable; pass a target dict or same-model identifier. Maps to Ironbug IB_BoilerHotWater field EfficiencyCurveTemperatureEvaluationVariable.'),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design hot-water flow rate; maps to Ironbug IB_BoilerHotWater field DesignWaterFlowRate.'),
        ] = None,
        minimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumPartLoadRatio value; maps to Ironbug IB_BoilerHotWater field MinimumPartLoadRatio.'),
        ] = None,
        maximum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional MaximumPartLoadRatio value; maps to Ironbug IB_BoilerHotWater field MaximumPartLoadRatio.'),
        ] = None,
        optimum_part_load_ratio: Annotated[
            float | None,
            Field(description='Optional OptimumPartLoadRatio value; maps to Ironbug IB_BoilerHotWater field OptimumPartLoadRatio.'),
        ] = None,
        water_outlet_upper_temperature_limit: Annotated[
            float | None,
            Field(description='Optional WaterOutletUpperTemperatureLimit value; maps to Ironbug IB_BoilerHotWater field WaterOutletUpperTemperatureLimit.'),
        ] = None,
        boiler_flow_mode: Annotated[
            str | None,
            Field(description='Optional boiler flow mode; maps to Ironbug IB_BoilerHotWater field BoilerFlowMode.'),
        ] = None,
        parasitic_electric_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional ParasiticElectricLoad value; maps to Ironbug IB_BoilerHotWater field ParasiticElectricLoad.'),
        ] = None,
        on_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional OnCycleParasiticElectricLoad value; maps to Ironbug IB_BoilerHotWater field OnCycleParasiticElectricLoad.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Optional SizingFactor value; maps to Ironbug IB_BoilerHotWater field SizingFactor.'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EndUseSubcategory value; maps to Ironbug IB_BoilerHotWater field EndUseSubcategory.'),
        ] = None,
        off_cycle_parasitic_fuel_load: Annotated[
            float | None,
            Field(description='Optional OffCycleParasiticFuelLoad value; maps to Ironbug IB_BoilerHotWater field OffCycleParasiticFuelLoad.'),
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
        """Create IB_BoilerHotWater as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if nominal_thermal_efficiency is not None:
            source_fields['NominalThermalEfficiency'] = nominal_thermal_efficiency
        if normalized_boiler_efficiency_curve_target is not None:
            source_field_targets['NormalizedBoilerEfficiencyCurve'] = normalized_boiler_efficiency_curve_target
        source_properties: dict[str, Any] = {}
        if efficiency_curve_temperature_evaluation_variable_target is not None:
            source_field_targets['EfficiencyCurveTemperatureEvaluationVariable'] = efficiency_curve_temperature_evaluation_variable_target
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if minimum_part_load_ratio is not None:
            source_fields['MinimumPartLoadRatio'] = minimum_part_load_ratio
        if maximum_part_load_ratio is not None:
            source_fields['MaximumPartLoadRatio'] = maximum_part_load_ratio
        if optimum_part_load_ratio is not None:
            source_fields['OptimumPartLoadRatio'] = optimum_part_load_ratio
        if water_outlet_upper_temperature_limit is not None:
            source_fields['WaterOutletUpperTemperatureLimit'] = water_outlet_upper_temperature_limit
        if boiler_flow_mode is not None:
            source_fields['BoilerFlowMode'] = boiler_flow_mode
        if parasitic_electric_load is not None:
            source_fields['ParasiticElectricLoad'] = parasitic_electric_load
        if on_cycle_parasitic_electric_load is not None:
            source_fields['OnCycleParasiticElectricLoad'] = on_cycle_parasitic_electric_load
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if off_cycle_parasitic_fuel_load is not None:
            source_fields['OffCycleParasiticFuelLoad'] = off_cycle_parasitic_fuel_load
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_BoilerHotWater',
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
