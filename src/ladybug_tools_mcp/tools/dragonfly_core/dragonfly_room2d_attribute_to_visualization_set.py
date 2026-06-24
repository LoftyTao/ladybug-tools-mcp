"""Create Dragonfly Room2D attribute VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.display import (
    dragonfly_room2d_attribute_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_room2d_attribute_to_visualization_set tool."""

    @mcp.tool(
        name="room2d_attribute_to_visualization_set",
        description=(
            "Create a compact VisualizationSet preview from df_room2ds_by_attribute "
            "output. Use this after Room2D attribute screening to visually inspect the "
            "matched Room2Ds and groups. Set return_visualization_set=false to save the "
            "preview and return visualization_set_target for shared exporters. Returns "
            "summary_view with attribute/group metadata, report, and optionally the "
            "VisualizationSet body."
        ),
        tags={"dragonfly", "room2d", "attribute", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_room2d_attribute_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        attribute_result: Annotated[
            dict[str, Any],
            Field(description="Result dictionary returned by df_room2ds_by_attribute, including selection and groups."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly Room2D attribute VisualizationSet."""
        return service(
            garden_root=garden_root,
            attribute_result=attribute_result,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
