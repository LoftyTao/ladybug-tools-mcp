"""Dragonfly Electric Grid results VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the Grid results VisualizationSet handoff tool."""

    @mcp.tool(
        name="DF_grid_results_to_visualization_set",
        description=(
            "Create a compact Ladybug Display VisualizationSet target for "
            "registered Dragonfly Grid OpenDSS result artifacts. Use shared "
            "visualization exporters for SVG, HTML, or vtk.js output."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "result", "visualization", "visualization-set", "target"},
        timeout=20,
    )
    def grid_results_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        result_targets: Annotated[list[dict[str, Any]], Field(description="Registered OpenDSS CSV result artifact targets.")],
        name: Annotated[str, Field(description="VisualizationSet identifier/display name.")] = "OpenDSS Results",
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict; keep false for compact target handoff.")] = False,
    ) -> dict[str, Any]:
        """Create a VisualizationSet target for Electric Grid result artifacts."""
        from garden.dragonfly_grid.display import grid_results_to_visualization_set as service

        return service(
            garden_root=garden_root,
            result_targets=result_targets,
            name=name,
            return_visualization_set=return_visualization_set,
        )
