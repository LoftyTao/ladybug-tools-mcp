'MCP tool for detailed_hvac_shading_surface.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_shading_surface tool.'

    @mcp.tool(
        name='shading_surface',
        description=(
            'Create IB_ShadingSurface, an Ironbug wrapper for an OpenStudio ShadingSurface / EnergyPlus Shading:Site:Detailed surface from explicit 3D vertices. Use it when another Ironbug DetailedHVAC object, such as a flat-plate solar collector, needs a shading-surface target; it does not create Honeybee Shade geometry or Radiance context. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'shading', 'surface', 'geometry', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_shading_surface(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
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
            Field(description="Stable identifier for the new IB_ShadingSurface object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        points: Annotated[
            list[str] | None,
            Field(
                description="Optional world-coordinate vertices as 'x,y,z' strings in meters; provide at least three points for the shading surface."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug OpenStudio shading surface from vertices."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if points is not None:
            source_properties['Points'] = points
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ShadingSurface',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
