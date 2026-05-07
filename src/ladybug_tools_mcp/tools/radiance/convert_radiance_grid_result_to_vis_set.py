"""Verbose Radiance grid VisualizationSet alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_grid_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the convert_radiance_grid_result_to_vis_set alias tool."""

    @mcp.tool(
        name="convert_radiance_grid_result_to_vis_set",
        description="Alias for radiance_grid_result_to_visualization_set. Convert a completed Radiance grid result to a VisualizationSet target.",
        tags={"radiance", "grid", "visualization-set", "alias", "write", "safe"},
        timeout=60,
    )
    def convert_radiance_grid_result_to_vis_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Optional completed radiance_run target.")] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier when run_target is omitted.")] = None,
        grid_data_path: Annotated[str | None, Field(description="Optional Garden-relative folder containing grids_info.json.")] = None,
        grid_results_path: Annotated[str | None, Field(description="Optional alias for grid_data_path.")] = None,
        model_target: Annotated[dict[str, Any] | None, Field(description="Optional model target override.")] = None,
        grid_index: Annotated[int | None, Field(description="Optional Agent index hint. Ignored.")] = None,
        name: Annotated[str, Field(description="VisualizationSet identifier and artifact name.")] = "radiance_grid_result",
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict.")] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from Radiance grid results through a verbose alias."""
        if grid_data_path is None and grid_results_path is not None:
            grid_data_path = grid_results_path
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            grid_data_path=grid_data_path,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
