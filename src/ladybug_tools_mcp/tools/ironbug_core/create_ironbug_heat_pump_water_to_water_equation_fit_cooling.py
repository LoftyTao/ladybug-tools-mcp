'MCP tool for detailed_hvac_heat_pump_water_to_water_equation_fit_cooling.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_heat_pump_water_to_water_equation_fit_cooling tool.'

    @mcp.tool(
        name='heat_pump_water_to_water_equation_fit_cooling',
        description=(
            'Create an Ironbug IB_HeatPumpWaterToWaterEquationFitCooling object for EnergyPlus/OpenStudio HeatPump:WaterToWater:EquationFit:Cooling. Use this simple curve-fit water-to-water heat pump on plant loops with load-side and source-side water connections; it is heat-pump plant equipment, not a hydronic Pump:* object. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'heat-pump',
            'water-to-water',
            'equation-fit',
            'cooling',
            'plant-loop',
            'plant-component',
            'curve',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_heat_pump_water_to_water_equation_fit_cooling(
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
            Field(description="Stable DetailedHVAC object identifier for this water-to-water equation-fit cooling heat pump."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        reference_load_side_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional reference load-side water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_load_side_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description="Optional rated load-side water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        reference_source_side_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional reference source-side water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_source_side_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description="Optional rated source-side water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_cooling_capacity: Annotated[
            str | float | int | bool | None,
            Field(description="Optional reference cooling capacity in W, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_cooling_power_consumption: Annotated[
            str | float | int | bool | None,
            Field(description="Optional reference cooling compressor power consumption in W, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        cooling_capacity_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for the quadvariate cooling capacity curve."),
        ] = None,
        cooling_capacity_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the equation-fit cooling capacity curve when not using a curve target."),
        ] = None,
        cooling_capacity_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the equation-fit cooling capacity curve when not using a curve target."),
        ] = None,
        cooling_capacity_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the equation-fit cooling capacity curve when not using a curve target."),
        ] = None,
        cooling_capacity_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the equation-fit cooling capacity curve when not using a curve target."),
        ] = None,
        cooling_capacity_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the equation-fit cooling capacity curve when not using a curve target."),
        ] = None,
        cooling_compressor_power_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for the quadvariate cooling compressor power curve."),
        ] = None,
        cooling_compressor_power_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the cooling compressor power curve when not using a curve target."),
        ] = None,
        cooling_compressor_power_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the cooling compressor power curve when not using a curve target."),
        ] = None,
        cooling_compressor_power_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the cooling compressor power curve when not using a curve target."),
        ] = None,
        cooling_compressor_power_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the cooling compressor power curve when not using a curve target."),
        ] = None,
        cooling_compressor_power_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the cooling compressor power curve when not using a curve target."),
        ] = None,
        reference_coefficientof_performance: Annotated[
            float | None,
            Field(description="Optional reference cooling COP in W/W; EnergyPlus can use it to autosize compressor power."),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description="Optional sizing multiplier for autosized cooling capacity and flow rates."),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_HeatPumpWaterToWaterEquationFitCooling as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if reference_load_side_flow_rate is not None:
            source_fields['ReferenceLoadSideFlowRate'] = reference_load_side_flow_rate
        if rated_load_side_flow_rate is not None:
            source_fields['RatedLoadSideFlowRate'] = rated_load_side_flow_rate
        if reference_source_side_flow_rate is not None:
            source_fields['ReferenceSourceSideFlowRate'] = reference_source_side_flow_rate
        if rated_source_side_flow_rate is not None:
            source_fields['RatedSourceSideFlowRate'] = rated_source_side_flow_rate
        if rated_cooling_capacity is not None:
            source_fields['RatedCoolingCapacity'] = rated_cooling_capacity
        if rated_cooling_power_consumption is not None:
            source_fields['RatedCoolingPowerConsumption'] = rated_cooling_power_consumption
        if cooling_capacity_curve_target is not None:
            source_field_targets['CoolingCapacityCurve'] = cooling_capacity_curve_target
        if cooling_capacity_coefficient1 is not None:
            source_fields['CoolingCapacityCoefficient1'] = cooling_capacity_coefficient1
        if cooling_capacity_coefficient2 is not None:
            source_fields['CoolingCapacityCoefficient2'] = cooling_capacity_coefficient2
        if cooling_capacity_coefficient3 is not None:
            source_fields['CoolingCapacityCoefficient3'] = cooling_capacity_coefficient3
        if cooling_capacity_coefficient4 is not None:
            source_fields['CoolingCapacityCoefficient4'] = cooling_capacity_coefficient4
        if cooling_capacity_coefficient5 is not None:
            source_fields['CoolingCapacityCoefficient5'] = cooling_capacity_coefficient5
        if cooling_compressor_power_curve_target is not None:
            source_field_targets['CoolingCompressorPowerCurve'] = cooling_compressor_power_curve_target
        if cooling_compressor_power_coefficient1 is not None:
            source_fields['CoolingCompressorPowerCoefficient1'] = cooling_compressor_power_coefficient1
        if cooling_compressor_power_coefficient2 is not None:
            source_fields['CoolingCompressorPowerCoefficient2'] = cooling_compressor_power_coefficient2
        if cooling_compressor_power_coefficient3 is not None:
            source_fields['CoolingCompressorPowerCoefficient3'] = cooling_compressor_power_coefficient3
        if cooling_compressor_power_coefficient4 is not None:
            source_fields['CoolingCompressorPowerCoefficient4'] = cooling_compressor_power_coefficient4
        if cooling_compressor_power_coefficient5 is not None:
            source_fields['CoolingCompressorPowerCoefficient5'] = cooling_compressor_power_coefficient5
        if reference_coefficientof_performance is not None:
            source_fields['ReferenceCoefficientofPerformance'] = reference_coefficientof_performance
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HeatPumpWaterToWaterEquationFitCooling',
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
