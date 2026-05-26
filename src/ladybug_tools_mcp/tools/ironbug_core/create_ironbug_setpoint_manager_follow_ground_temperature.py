'MCP tool for detailed_hvac_setpoint_manager_follow_ground_temperature.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_follow_ground_temperature tool.'

    @mcp.tool(
        name='setpoint_manager_follow_ground_temperature',
        description=(
            'Create IB_SetpointManagerFollowGroundTemperature / EnergyPlus SetpointManager:FollowGroundTemperature. The manager follows a selected Site:GroundTemperature object, applies an offset, and clips the resulting node setpoint between minimum and maximum temperatures. This authors Ironbug DetailedHVAC input only; it is not a ground heat exchanger, ground-temperature file, weather source, result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'follow', 'ground-temperature', 'ground-loop', 'plant-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_follow_ground_temperature(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json; for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_SetpointManagerFollowGroundTemperature object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        reference_ground_temperature_object_type: Annotated[
            str | None,
            Field(description='Optional Site:GroundTemperature object type to follow, such as BuildingSurface, Shallow, Deep, or FCfactorMethod; maps to Ironbug IB_SetpointManagerFollowGroundTemperature field ReferenceGroundTemperatureObjectType.'),
        ] = None,
        offset_temperature_difference: Annotated[
            float | None,
            Field(description='Optional temperature offset in deg C applied to the selected ground temperature before limits; maps to Ironbug field OffsetTemperatureDifference.'),
        ] = None,
        maximum_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional upper limit in deg C for the calculated setpoint; maps to Ironbug field MaximumSetpointTemperature.'),
        ] = None,
        minimum_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional lower limit in deg C for the calculated setpoint; maps to Ironbug field MinimumSetpointTemperature.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerFollowGroundTemperature field Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:FollowGroundTemperature target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if reference_ground_temperature_object_type is not None:
            source_fields['ReferenceGroundTemperatureObjectType'] = reference_ground_temperature_object_type
        if offset_temperature_difference is not None:
            source_fields['OffsetTemperatureDifference'] = offset_temperature_difference
        if maximum_setpoint_temperature is not None:
            source_fields['MaximumSetpointTemperature'] = maximum_setpoint_temperature
        if minimum_setpoint_temperature is not None:
            source_fields['MinimumSetpointTemperature'] = minimum_setpoint_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerFollowGroundTemperature',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
