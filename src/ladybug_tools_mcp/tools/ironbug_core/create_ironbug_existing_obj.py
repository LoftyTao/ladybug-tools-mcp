'MCP tool for detailed_hvac_existing_obj.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_existing_obj tool.'

    @mcp.tool(
        name='existing_obj',
        description=(
            'Create IB_ExistingObj, an Ironbug reference to a named object in an existing OpenStudio Model (.osm) imported by Ironbug. Use it as the ExistingObj child for IB_ExistAirLoop or IB_ExistPlantLoop; it records Name and OsmFile and does not import, discover, or validate the OSM file. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'component', 'existing-object', 'openstudio', 'author'},
        timeout=20,
    )
    def create_ironbug_existing_obj(
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
            Field(description="Stable identifier for the new IB_ExistingObj object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional name of the existing OpenStudio object, for example an AirLoopHVAC or PlantLoop name from an imported OSM file."
            ),
        ] = None,
        osm_file: Annotated[
            str | None,
            Field(
                description="Optional path to the OpenStudio Model (.osm) file that contains the named existing object."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ExistingObj as a reviewed Ironbug Base Class authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_properties['Name'] = name
        if osm_file is not None:
            source_properties['OsmFile'] = osm_file
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ExistingObj',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
