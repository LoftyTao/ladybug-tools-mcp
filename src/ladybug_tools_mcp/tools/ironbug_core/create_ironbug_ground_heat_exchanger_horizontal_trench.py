'MCP tool for detailed_hvac_ground_heat_exchanger_horizontal_trench.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_ground_heat_exchanger_horizontal_trench tool.'

    @mcp.tool(
        name='ground_heat_exchanger_horizontal_trench',
        description=(
            'Create IB_GroundHeatExchangerHorizontalTrench, an OpenStudio/EnergyPlus GroundHeatExchanger:HorizontalTrench plant-loop ground heat exchanger for buried pipe trenches. Use it for geothermal/source-loop trench length, pipe spacing, burial depth, soil/pipe thermal properties, and ground-temperature inputs; this is not a vertical borehole field, fluid-to-fluid heat exchanger, heat pump, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
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
            'trench',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_ground_heat_exchanger_horizontal_trench(
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
            Field(description="Stable identifier for the new IB_GroundHeatExchangerHorizontalTrench object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        design_flow_rate: Annotated[
            float | None,
            Field(description='Optional design flow rate in m3/s for the horizontal trench ground heat exchanger; maps to DesignFlowRate.'),
        ] = None,
        trench_lengthin_pipe_axial_direction: Annotated[
            float | None,
            Field(description='Optional axial length of each buried pipe trench in meters; maps to TrenchLengthinPipeAxialDirection.'),
        ] = None,
        numberof_trenches: Annotated[
            int | None,
            Field(description='Optional number of single-pipe trenches in the horizontal ground heat exchanger; maps to NumberofTrenches.'),
        ] = None,
        horizontal_spacing_between_pipes: Annotated[
            float | None,
            Field(description='Optional HorizontalSpacingBetweenPipes value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field HorizontalSpacingBetweenPipes.'),
        ] = None,
        pipe_inner_diameter: Annotated[
            float | None,
            Field(description='Optional PipeInnerDiameter value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field PipeInnerDiameter.'),
        ] = None,
        pipe_outer_diameter: Annotated[
            float | None,
            Field(description='Optional PipeOuterDiameter value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field PipeOuterDiameter.'),
        ] = None,
        burial_depth: Annotated[
            float | None,
            Field(description='Optional pipe burial depth in meters from grade to pipe centroid; maps to BurialDepth.'),
        ] = None,
        soil_thermal_conductivity: Annotated[
            float | None,
            Field(description='Optional soil thermal conductivity in W/m-K for the trench simulation; maps to SoilThermalConductivity.'),
        ] = None,
        soil_density: Annotated[
            float | None,
            Field(description='Optional SoilDensity value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field SoilDensity.'),
        ] = None,
        soil_specific_heat: Annotated[
            float | None,
            Field(description='Optional SoilSpecificHeat value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field SoilSpecificHeat.'),
        ] = None,
        pipe_thermal_conductivity: Annotated[
            float | None,
            Field(description='Optional PipeThermalConductivity value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field PipeThermalConductivity.'),
        ] = None,
        pipe_density: Annotated[
            float | None,
            Field(description='Optional PipeDensity value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field PipeDensity.'),
        ] = None,
        pipe_specific_heat: Annotated[
            float | None,
            Field(description='Optional PipeSpecificHeat value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field PipeSpecificHeat.'),
        ] = None,
        soil_moisture_content_percent: Annotated[
            float | None,
            Field(description='Optional SoilMoistureContentPercent value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field SoilMoistureContentPercent.'),
        ] = None,
        soil_moisture_content_percentat_saturation: Annotated[
            float | None,
            Field(description='Optional SoilMoistureContentPercentatSaturation value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field SoilMoistureContentPercentatSaturation.'),
        ] = None,
        ground_temperature_model: Annotated[
            str | float | int | bool | None,
            Field(description='Optional undisturbed ground temperature model reference, such as a Kusuda-Achenbach model name; maps to GroundTemperatureModel.'),
        ] = None,
        kusuda_achenbach_average_surface_temperature: Annotated[
            str | float | int | bool | None,
            Field(description='Optional KusudaAchenbachAverageSurfaceTemperature value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field KusudaAchenbachAverageSurfaceTemperature.'),
        ] = None,
        kusuda_achenbach_average_amplitudeof_surface_temperature: Annotated[
            str | float | int | bool | None,
            Field(description='Optional KusudaAchenbachAverageAmplitudeofSurfaceTemperature value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field KusudaAchenbachAverageAmplitudeofSurfaceTemperature.'),
        ] = None,
        kusuda_achenbach_phase_shiftof_minimum_surface_temperature: Annotated[
            str | float | int | bool | None,
            Field(description='Optional KusudaAchenbachPhaseShiftofMinimumSurfaceTemperature value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field KusudaAchenbachPhaseShiftofMinimumSurfaceTemperature.'),
        ] = None,
        evapotranspiration_ground_cover_parameter: Annotated[
            float | None,
            Field(description='Optional EvapotranspirationGroundCoverParameter value; maps to Ironbug IB_GroundHeatExchangerHorizontalTrench field EvapotranspirationGroundCoverParameter.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this GroundHeatExchanger:HorizontalTrench; maps to Name.'),
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
        """Create IB_GroundHeatExchangerHorizontalTrench as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_flow_rate is not None:
            source_fields['DesignFlowRate'] = design_flow_rate
        if trench_lengthin_pipe_axial_direction is not None:
            source_fields['TrenchLengthinPipeAxialDirection'] = trench_lengthin_pipe_axial_direction
        if numberof_trenches is not None:
            source_fields['NumberofTrenches'] = numberof_trenches
        if horizontal_spacing_between_pipes is not None:
            source_fields['HorizontalSpacingBetweenPipes'] = horizontal_spacing_between_pipes
        if pipe_inner_diameter is not None:
            source_fields['PipeInnerDiameter'] = pipe_inner_diameter
        if pipe_outer_diameter is not None:
            source_fields['PipeOuterDiameter'] = pipe_outer_diameter
        if burial_depth is not None:
            source_fields['BurialDepth'] = burial_depth
        if soil_thermal_conductivity is not None:
            source_fields['SoilThermalConductivity'] = soil_thermal_conductivity
        if soil_density is not None:
            source_fields['SoilDensity'] = soil_density
        if soil_specific_heat is not None:
            source_fields['SoilSpecificHeat'] = soil_specific_heat
        if pipe_thermal_conductivity is not None:
            source_fields['PipeThermalConductivity'] = pipe_thermal_conductivity
        if pipe_density is not None:
            source_fields['PipeDensity'] = pipe_density
        if pipe_specific_heat is not None:
            source_fields['PipeSpecificHeat'] = pipe_specific_heat
        if soil_moisture_content_percent is not None:
            source_fields['SoilMoistureContentPercent'] = soil_moisture_content_percent
        if soil_moisture_content_percentat_saturation is not None:
            source_fields['SoilMoistureContentPercentatSaturation'] = soil_moisture_content_percentat_saturation
        if ground_temperature_model is not None:
            source_fields['GroundTemperatureModel'] = ground_temperature_model
        if kusuda_achenbach_average_surface_temperature is not None:
            source_fields['KusudaAchenbachAverageSurfaceTemperature'] = kusuda_achenbach_average_surface_temperature
        if kusuda_achenbach_average_amplitudeof_surface_temperature is not None:
            source_fields['KusudaAchenbachAverageAmplitudeofSurfaceTemperature'] = kusuda_achenbach_average_amplitudeof_surface_temperature
        if kusuda_achenbach_phase_shiftof_minimum_surface_temperature is not None:
            source_fields['KusudaAchenbachPhaseShiftofMinimumSurfaceTemperature'] = kusuda_achenbach_phase_shiftof_minimum_surface_temperature
        if evapotranspiration_ground_cover_parameter is not None:
            source_fields['EvapotranspirationGroundCoverParameter'] = evapotranspiration_ground_cover_parameter
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GroundHeatExchangerHorizontalTrench',
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
