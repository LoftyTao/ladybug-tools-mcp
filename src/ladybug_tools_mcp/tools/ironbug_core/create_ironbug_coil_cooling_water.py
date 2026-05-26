'MCP tool for detailed_hvac_coil_cooling_water.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_water tool.'

    @mcp.tool(
        name='coil_cooling_water',
        description=(
            'Create IB_CoilCoolingWater, an Ironbug chilled-water cooling coil component '
            'that maps downstream to EnergyPlus Coil:Cooling:Water and OpenStudio '
            'CoilCoolingWater. Use it as an FCU cooling coil, unit-ventilator coil, '
            'or air-side cooling coil target that must later be placed in valid '
            'equipment and connected to a chilled-water PlantLoop. This authors '
            'Ironbug DetailedHVAC input, not a Honeybee Energy HVAC template. Returns '
            'target, summary_view, persistence_receipt, and report for downstream '
            'DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'coil',
            'chilled-water',
            'plant-loop',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_cooling_water(
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
            Field(description="Stable identifier for the new IB_CoilCoolingWater object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the cooling coil available.'),
        ] = None,
        available_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional legacy AvailableSchedule target for Ironbug/OpenStudio source compatibility; prefer availability_schedule_target when both are available.'),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design chilled-water flow rate in m3/s or Autosize where supported; maps to EnergyPlus Design Water Flow Rate.'),
        ] = None,
        design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design air flow rate in m3/s or Autosize where supported by the final air-side placement.'),
        ] = None,
        design_inlet_water_temperature: Annotated[
            float | str | None,
            Field(description='Optional design entering chilled-water temperature in Celsius or Autosize where supported.'),
        ] = None,
        design_inlet_air_temperature: Annotated[
            float | str | None,
            Field(description='Optional design entering air temperature in Celsius or Autosize where supported.'),
        ] = None,
        design_outlet_air_temperature: Annotated[
            float | str | None,
            Field(description='Optional design leaving air temperature in Celsius or Autosize where supported.'),
        ] = None,
        design_inlet_air_humidity_ratio: Annotated[
            float | str | None,
            Field(description='Optional DesignInletAirHumidityRatio value; maps to Ironbug IB_CoilCoolingWater field DesignInletAirHumidityRatio.'),
        ] = None,
        design_outlet_air_humidity_ratio: Annotated[
            float | str | None,
            Field(description='Optional DesignOutletAirHumidityRatio value; maps to Ironbug IB_CoilCoolingWater field DesignOutletAirHumidityRatio.'),
        ] = None,
        type_of_analysis: Annotated[
            str | None,
            Field(description='Optional cooling coil analysis mode, commonly SimpleAnalysis or DetailedAnalysis for Coil:Cooling:Water.'),
        ] = None,
        heat_exchanger_configuration: Annotated[
            str | None,
            Field(description='Optional heat exchanger configuration, commonly CrossFlow or CounterFlow for Coil:Cooling:Water.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingWater field Name.'),
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
        controller_water_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ControllerWaterCoil target or same-model identifier. "
                    "Controllers are applied when this chilled-water coil is added to a valid loop node."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilCoolingWater as a reviewed chilled-water coil component."""

        child_targets = [
            controller_water_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if available_schedule_target is not None:
            source_field_targets['AvailableSchedule'] = available_schedule_target
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if design_air_flow_rate is not None:
            source_fields['DesignAirFlowRate'] = design_air_flow_rate
        if design_inlet_water_temperature is not None:
            source_fields['DesignInletWaterTemperature'] = design_inlet_water_temperature
        if design_inlet_air_temperature is not None:
            source_fields['DesignInletAirTemperature'] = design_inlet_air_temperature
        if design_outlet_air_temperature is not None:
            source_fields['DesignOutletAirTemperature'] = design_outlet_air_temperature
        if design_inlet_air_humidity_ratio is not None:
            source_fields['DesignInletAirHumidityRatio'] = design_inlet_air_humidity_ratio
        if design_outlet_air_humidity_ratio is not None:
            source_fields['DesignOutletAirHumidityRatio'] = design_outlet_air_humidity_ratio
        if type_of_analysis is not None:
            source_fields['TypeOfAnalysis'] = type_of_analysis
        if heat_exchanger_configuration is not None:
            source_fields['HeatExchangerConfiguration'] = heat_exchanger_configuration
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingWater',
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
