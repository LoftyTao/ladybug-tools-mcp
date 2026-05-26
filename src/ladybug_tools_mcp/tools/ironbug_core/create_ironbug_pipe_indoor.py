'MCP tool for detailed_hvac_pipe_indoor.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_pipe_indoor tool.'

    @mcp.tool(
        name='pipe_indoor',
        description=(
            'Create IB_PipeIndoor, an EnergyPlus Pipe:Indoor plant-loop pipe with transport delay and heat transfer to a zone or scheduled indoor environment. Use it with an Energy construction name, ambient ThermalZone or schedules, pipe diameter, and pipe length; this is not a pass-through Pipe:Adiabatic, outdoor pipe, pump, duct, Honeybee geometry pipe, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'plant-loop', 'plant-component', 'pipe', 'indoor-pipe', 'heat-transfer', 'thermal-zone', 'construction', 'schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_pipe_indoor(
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
            Field(description="Stable identifier for the new IB_PipeIndoor object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        environment_type: Annotated[
            str | None,
            Field(description='Optional indoor pipe environment type, usually Zone or Schedule; maps to EnvironmentType.'),
        ] = None,
        ambient_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the ambient air temperature around the indoor pipe; maps to AmbientTemperatureSchedule.'),
        ] = None,
        ambient_air_velocity_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for local air velocity around the indoor pipe; maps to AmbientAirVelocitySchedule.'),
        ] = None,
        pipe_inside_diameter: Annotated[
            float | None,
            Field(description='Optional pipe inside diameter in m for Pipe:Indoor heat transfer; maps to PipeInsideDiameter.'),
        ] = None,
        pipe_length: Annotated[
            float | None,
            Field(description='Optional pipe length in m for Pipe:Indoor heat transfer; maps to PipeLength.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this Pipe:Indoor plant-loop pipe; maps to Name.'),
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
        ambient_temperature_zone: Annotated[
            str | None,
            Field(
                description=(
                    "Optional ambient ThermalZone room/name string for a Zone environment; "
                    "stored as source private property _zoneName."
                )
            ),
        ] = None,
        ambient_temperature_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier whose room name "
                    "becomes the ambient zone for this Pipe:Indoor object."
                )
            ),
        ] = None,
        construction_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Energy construction target or construction identifier for "
                    "the Pipe:Indoor wall/insulation construction name."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug Pipe:Indoor plant-loop heat-transfer pipe."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if environment_type is not None:
            source_fields['EnvironmentType'] = environment_type
        if ambient_temperature_schedule_target is not None:
            source_field_targets['AmbientTemperatureSchedule'] = ambient_temperature_schedule_target
        if ambient_air_velocity_schedule_target is not None:
            source_field_targets['AmbientAirVelocitySchedule'] = ambient_air_velocity_schedule_target
        if pipe_inside_diameter is not None:
            source_fields['PipeInsideDiameter'] = pipe_inside_diameter
        if pipe_length is not None:
            source_fields['PipeLength'] = pipe_length
        ib_properties: dict[str, Any] = {}
        if construction_target is not None:
            ib_properties['_construction'] = target_identifier(
                construction_target,
                parameter_name="construction_target",
            )
        if ambient_temperature_zone_target is not None:
            ib_properties['_zoneName'] = target_identifier(
                ambient_temperature_zone_target,
                parameter_name="ambient_temperature_zone_target",
            )
        if ambient_temperature_zone is not None:
            ib_properties['_zoneName'] = ambient_temperature_zone
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PipeIndoor',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
