"""Create Dragonfly Building VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DF_building_to_visualization_set tool."""

    @mcp.tool(
        name="DF_building_to_visualization_set",
        description=(
            "Create a compact VisualizationSet preview for one Dragonfly Building "
            "target. Pass a Dragonfly object target from DF_search_objects or a "
            "creation/edit tool. Set return_visualization_set=false to save the "
            "preview and return visualization_set_target for shared exporters like "
            "LB_set_to_svg or LB_set_to_vtkjs. Returns "
            "summary_view, report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "building", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_building_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        target: Annotated[dict[str, Any], Field(description="Dragonfly Building object target.")],
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
        """Create a Dragonfly Building VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_building_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
