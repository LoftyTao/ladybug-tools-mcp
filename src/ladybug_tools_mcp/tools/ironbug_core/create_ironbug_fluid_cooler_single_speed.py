'MCP tool for detailed_hvac_fluid_cooler_single_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_fluid_cooler_single_speed tool.'

    @mcp.tool(
        name='fluid_cooler_single_speed',
        description=(
            'Create IB_FluidCoolerSingleSpeed, an OpenStudio/EnergyPlus FluidCooler:SingleSpeed condenser-water plant-loop heat-rejection component with a single-speed fan. Use it for dry fluid-cooler UA or nominal-capacity inputs, design water and air flow, and fan power; this is not an evaporative fluid cooler, cooling tower, chiller, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'plant-loop', 'plant-component', 'condenser-water', 'heat-rejection', 'fluid-cooler', 'cooling', 'single-speed', 'author'},
        timeout=20,
    )
    def create_ironbug_fluid_cooler_single_speed(
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
            Field(description="Stable identifier for the new IB_FluidCoolerSingleSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Optional performance input method for FluidCooler:SingleSpeed; accepted values include UFactorTimesAreaAndDesignWaterFlowRate and NominalCapacity.'),
        ] = None,
        design_air_flow_rate_ufactor_times_area_value: Annotated[
            float | str | None,
            Field(description='Optional design air-flow UA value for the single-speed fluid cooler when PerformanceInputMethod uses UA and design water flow.'),
        ] = None,
        nominal_capacity: Annotated[
            float | None,
            Field(description='Optional nominal heat-rejection capacity in W for the single-speed fluid cooler.'),
        ] = None,
        design_entering_water_temperature: Annotated[
            float | None,
            Field(description='Optional design entering condenser-water temperature in C at nominal fluid-cooler conditions.'),
        ] = None,
        design_entering_air_temperature: Annotated[
            float | None,
            Field(description='Optional design entering outdoor-air dry-bulb temperature in C at nominal fluid-cooler conditions.'),
        ] = None,
        design_entering_air_wetbulb_temperature: Annotated[
            float | None,
            Field(description='Optional design entering outdoor-air wet-bulb temperature in C at nominal fluid-cooler conditions.'),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design condenser-water flow rate through the fluid cooler in m3/s, or Autosize when supported.'),
        ] = None,
        design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design outdoor-air flow rate induced by the fluid-cooler fan in m3/s, or Autosize when supported.'),
        ] = None,
        design_air_flow_rate_fan_power: Annotated[
            float | str | None,
            Field(description='Optional fan power in W at the design air flow rate, or Autosize when supported.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the single-speed fluid cooler object.'),
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
        """Create IB_FluidCoolerSingleSpeed as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if design_air_flow_rate_ufactor_times_area_value is not None:
            source_fields['DesignAirFlowRateUfactorTimesAreaValue'] = design_air_flow_rate_ufactor_times_area_value
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if design_entering_water_temperature is not None:
            source_fields['DesignEnteringWaterTemperature'] = design_entering_water_temperature
        if design_entering_air_temperature is not None:
            source_fields['DesignEnteringAirTemperature'] = design_entering_air_temperature
        if design_entering_air_wetbulb_temperature is not None:
            source_fields['DesignEnteringAirWetbulbTemperature'] = design_entering_air_wetbulb_temperature
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if design_air_flow_rate is not None:
            source_fields['DesignAirFlowRate'] = design_air_flow_rate
        if design_air_flow_rate_fan_power is not None:
            source_fields['DesignAirFlowRateFanPower'] = design_air_flow_rate_fan_power
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_FluidCoolerSingleSpeed',
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
