"""Create Dragonfly selection VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DF_selection_to_visualization_set tool."""

    @mcp.tool(
        name="DF_selection_to_visualization_set",
        description=(
            "Create a compact VisualizationSet preview from a dragonfly_selection "
            "returned by DF_search_objects or DF_room2ds_by_attribute. This is the "
            "preferred bridge from search/list screening into visual review. Set "
            "return_visualization_set=false to save the preview and return "
            "visualization_set_target for shared exporters. Returns summary_view, "
            "report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "selection", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_selection_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        selection: Annotated[dict[str, Any], Field(description="dragonfly_selection dictionary returned by Dragonfly search/list tools.")],
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
        """Create a Dragonfly selection VisualizationSet."""
        from garden.dragonfly_core.display import dragonfly_selection_to_visualization_set as service

        return service(
            garden_root=garden_root,
            selection=selection,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
