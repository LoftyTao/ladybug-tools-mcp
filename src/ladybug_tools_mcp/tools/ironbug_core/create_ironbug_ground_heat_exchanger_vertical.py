'MCP tool for detailed_hvac_ground_heat_exchanger_vertical.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_ground_heat_exchanger_vertical tool.'

    @mcp.tool(
        name='ground_heat_exchanger_vertical',
        description=(
            'Create IB_GroundHeatExchangerVertical, an OpenStudio/EnergyPlus vertical ground heat exchanger plant-loop component for geothermal borehole fields. Use it for borehole count/depth/length/radius, ground/grout/pipe thermal properties, and g-function response pairs; this is not a horizontal trench, fluid-to-fluid heat exchanger, heat pump, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'plant-loop',
            'plant-component',
            'heat-exchanger',
            'ground-heat-exchanger',
            'ground-loop',
            'geothermal',
            'borehole',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_ground_heat_exchanger_vertical(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_GroundHeatExchangerVertical object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        g_functions: Annotated[
            list[str | float] | None,
            Field(
                description=(
                    "Optional alternating g-function Ln(T/Ts) and value items for the vertical borehole response factors. "
                    "Pass pairs in the same order as the Ironbug Grasshopper GFunctions parameter."
                )
            ),
        ] = None,
        design_flow_rate: Annotated[
            float | None,
            Field(description='Optional total design flow rate in m3/s for the vertical borehole field; maps to DesignFlowRate.'),
        ] = None,
        numberof_bore_holes: Annotated[
            int | None,
            Field(description='Optional number of vertical boreholes in the ground heat exchanger field; maps to NumberofBoreHoles.'),
        ] = None,
        bore_hole_top_depth: Annotated[
            float | None,
            Field(description='Optional BoreHoleTopDepth value; maps to Ironbug IB_GroundHeatExchangerVertical field BoreHoleTopDepth.'),
        ] = None,
        bore_hole_length: Annotated[
            float | None,
            Field(description='Optional active vertical borehole length in meters; maps to BoreHoleLength.'),
        ] = None,
        bore_hole_radius: Annotated[
            float | None,
            Field(description='Optional vertical borehole radius in meters for the response-factor model; maps to BoreHoleRadius.'),
        ] = None,
        ground_thermal_conductivity: Annotated[
            float | None,
            Field(description='Optional ground thermal conductivity in W/m-K for the borehole field; maps to GroundThermalConductivity.'),
        ] = None,
        ground_thermal_heat_capacity: Annotated[
            float | None,
            Field(description='Optional GroundThermalHeatCapacity value; maps to Ironbug IB_GroundHeatExchangerVertical field GroundThermalHeatCapacity.'),
        ] = None,
        ground_temperature: Annotated[
            float | None,
            Field(description='Optional GroundTemperature value; maps to Ironbug IB_GroundHeatExchangerVertical field GroundTemperature.'),
        ] = None,
        grout_thermal_conductivity: Annotated[
            float | None,
            Field(description='Optional borehole grout thermal conductivity in W/m-K; maps to GroutThermalConductivity.'),
        ] = None,
        pipe_thermal_conductivity: Annotated[
            float | None,
            Field(description='Optional PipeThermalConductivity value; maps to Ironbug IB_GroundHeatExchangerVertical field PipeThermalConductivity.'),
        ] = None,
        pipe_out_diameter: Annotated[
            float | None,
            Field(description='Optional PipeOutDiameter value; maps to Ironbug IB_GroundHeatExchangerVertical field PipeOutDiameter.'),
        ] = None,
        u_tube_distance: Annotated[
            float | None,
            Field(description='Optional UTubeDistance value; maps to Ironbug IB_GroundHeatExchangerVertical field UTubeDistance.'),
        ] = None,
        pipe_thickness: Annotated[
            float | None,
            Field(description='Optional PipeThickness value; maps to Ironbug IB_GroundHeatExchangerVertical field PipeThickness.'),
        ] = None,
        maximum_lengthof_simulation: Annotated[
            float | None,
            Field(description='Optional MaximumLengthofSimulation value; maps to Ironbug IB_GroundHeatExchangerVertical field MaximumLengthofSimulation.'),
        ] = None,
        g_function_reference_ratio: Annotated[
            float | None,
            Field(description='Optional borehole radius-to-length reference ratio for g-function correction; maps to GFunctionReferenceRatio.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this vertical ground heat exchanger; maps to Name.'),
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
        """Create IB_GroundHeatExchangerVertical as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_flow_rate is not None:
            source_fields['DesignFlowRate'] = design_flow_rate
        if numberof_bore_holes is not None:
            source_fields['NumberofBoreHoles'] = numberof_bore_holes
        if bore_hole_top_depth is not None:
            source_fields['BoreHoleTopDepth'] = bore_hole_top_depth
        if bore_hole_length is not None:
            source_fields['BoreHoleLength'] = bore_hole_length
        if bore_hole_radius is not None:
            source_fields['BoreHoleRadius'] = bore_hole_radius
        if ground_thermal_conductivity is not None:
            source_fields['GroundThermalConductivity'] = ground_thermal_conductivity
        if ground_thermal_heat_capacity is not None:
            source_fields['GroundThermalHeatCapacity'] = ground_thermal_heat_capacity
        if ground_temperature is not None:
            source_fields['GroundTemperature'] = ground_temperature
        if grout_thermal_conductivity is not None:
            source_fields['GroutThermalConductivity'] = grout_thermal_conductivity
        if pipe_thermal_conductivity is not None:
            source_fields['PipeThermalConductivity'] = pipe_thermal_conductivity
        if pipe_out_diameter is not None:
            source_fields['PipeOutDiameter'] = pipe_out_diameter
        if u_tube_distance is not None:
            source_fields['UTubeDistance'] = u_tube_distance
        if pipe_thickness is not None:
            source_fields['PipeThickness'] = pipe_thickness
        if maximum_lengthof_simulation is not None:
            source_fields['MaximumLengthofSimulation'] = maximum_lengthof_simulation
        if g_function_reference_ratio is not None:
            source_fields['GFunctionReferenceRatio'] = g_function_reference_ratio
        if g_functions is not None:
            if len(g_functions) % 2 != 0:
                raise ValueError("g_functions must contain alternating LN/value pairs.")
            source_properties["GFuncs"] = [
                {"Ln": float(g_functions[index]), "GValue": float(g_functions[index + 1])}
                for index in range(0, len(g_functions), 2)
            ]
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GroundHeatExchangerVertical',
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
