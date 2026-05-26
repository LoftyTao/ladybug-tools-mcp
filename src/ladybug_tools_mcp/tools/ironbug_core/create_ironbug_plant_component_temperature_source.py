'MCP tool for detailed_hvac_plant_component_temperature_source.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_plant_component_temperature_source tool.'

    @mcp.tool(
        name='plant_component_temperature_source',
        description=(
            'Create IB_PlantComponentTemperatureSource, an EnergyPlus PlantComponent:TemperatureSource for a known constant or scheduled fluid source temperature such as a river, well, or seawater loop. Use it on plant/condenser branches with design flow and source-temperature inputs; this is not district energy, a boiler, chiller, heat pump, result reader, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'plant-loop', 'plant-component', 'temperature-source', 'source-temperature', 'schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_plant_component_temperature_source(
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
            Field(description="Stable identifier for the new IB_PlantComponentTemperatureSource object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        design_volume_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional design volume flow rate in m3/s, or autosize string, for the temperature source; maps to DesignVolumeFlowRate.'),
        ] = None,
        temperature_specification_type: Annotated[
            str | None,
            Field(description='Optional source temperature mode, usually Constant or Scheduled; maps to TemperatureSpecificationType.'),
        ] = None,
        source_temperature: Annotated[
            float | None,
            Field(description='Optional constant source temperature in C when TemperatureSpecificationType is Constant; maps to SourceTemperature.'),
        ] = None,
        source_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for scheduled source temperature values in C; maps to SourceTemperatureSchedule.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this PlantComponent:TemperatureSource; maps to Name.'),
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
        """Create an Ironbug PlantComponent:TemperatureSource object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_volume_flow_rate is not None:
            source_fields['DesignVolumeFlowRate'] = design_volume_flow_rate
        if temperature_specification_type is not None:
            source_fields['TemperatureSpecificationType'] = temperature_specification_type
        if source_temperature is not None:
            source_fields['SourceTemperature'] = source_temperature
        if source_temperature_schedule_target is not None:
            source_field_targets['SourceTemperatureSchedule'] = source_temperature_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PlantComponentTemperatureSource',
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
