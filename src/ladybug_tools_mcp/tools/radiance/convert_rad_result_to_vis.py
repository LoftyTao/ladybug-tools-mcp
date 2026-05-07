"""Short Radiance result VisualizationSet alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_grid_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the convert_rad_result_to_vis alias tool."""

    @mcp.tool(
        name="convert_rad_result_to_vis",
        description="Short alias for radiance_grid_result_to_visualization_set. Converts a completed Radiance grid result to a VisualizationSet target.",
        tags={
            "honeybee-radiance",
            "radiance",
            "postprocess",
            "grid",
            "visualization-set",
            "visualize",
            "write",
            "safe",
            "alias",
        },
        timeout=60,
    )
    def convert_rad_result_to_vis(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Optional completed radiance_run target.")] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier when run_target is omitted.")] = None,
        output_type: Annotated[str | None, Field(description="Optional Agent hint such as grid. Ignored.")] = None,
        grid_index: Annotated[int | None, Field(description="Optional Agent index hint. Ignored.")] = None,
        grid_results_path: Annotated[str | None, Field(description="Optional alias for grid_data_path.")] = None,
        grid_data_path: Annotated[str | None, Field(description="Optional Garden-relative folder containing grids_info.json.")] = None,
        model_target: Annotated[dict[str, Any] | None, Field(description="Optional model target override.")] = None,
        name: Annotated[str, Field(description="VisualizationSet identifier and artifact name.")] = "radiance_grid_result",
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict.")] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from Radiance grid results through a short alias."""
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
