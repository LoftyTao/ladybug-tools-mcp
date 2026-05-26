'MCP tool for detailed_hvac_exist_air_loop.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_exist_air_loop tool.'

    @mcp.tool(
        name='exist_air_loop',
        description=(
            'Create IB_ExistAirLoop, an Ironbug AirLoopHVAC wrapper that binds to an existing OpenStudio air loop through an IB_ExistingObj reference. Use it when zones or terminals must attach to an AirLoopHVAC already present in an imported OSM model; this tool does not create a new air-loop topology, plant loop, or Energy simulation run. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-loop', 'existing-object', 'openstudio', 'author'},
        timeout=20,
    )
    def create_ironbug_exist_air_loop(
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
            Field(description="Stable identifier for the new IB_ExistAirLoop object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        existing_obj_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_ExistingObj target containing the existing OpenStudio AirLoopHVAC name and OSM file path."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ExistAirLoop as a reviewed Ironbug Loops authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        if existing_obj_target is not None:
            source_property_targets['ExistingObj'] = existing_obj_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ExistAirLoop',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            overwrite=overwrite,
        )
