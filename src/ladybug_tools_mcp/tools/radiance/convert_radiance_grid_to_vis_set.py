"""Radiance grid VisualizationSet alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_grid_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the convert_radiance_grid_to_vis_set alias tool."""

    @mcp.tool(
        name="convert_radiance_grid_to_vis_set",
        description="Alias for radiance_grid_result_to_visualization_set. Convert a completed Radiance SensorGrid result folder or run target to a VisualizationSet target.",
        tags={
            "honeybee-radiance",
            "radiance",
            "postprocess",
            "sensor-grid",
            "grid",
            "results",
            "visualization-set",
            "visualize",
            "write",
            "safe",
            "alias",
        },
        timeout=60,
    )
    def convert_radiance_grid_to_vis_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Optional completed radiance_run target.")] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier when run_target is omitted.")] = None,
        grid_data_path: Annotated[str | None, Field(description="Optional Garden-relative folder containing grids_info.json.")] = None,
        grid_results_path: Annotated[str | None, Field(description="Optional alias for grid_data_path.")] = None,
        output_name: Annotated[str | None, Field(description="Optional run output name.")] = None,
        result_subfolder: Annotated[str | None, Field(description="Optional subfolder inside the selected output.")] = None,
        model_target: Annotated[dict[str, Any] | None, Field(description="Optional model target override.")] = None,
        color_by: Annotated[str | None, Field(description="Model context coloring: type, boundary_condition, or none.")] = "none",
        include_wireframe: Annotated[bool, Field(description="Include model wireframe context.")] = True,
        use_mesh: Annotated[bool, Field(description="Whether model context geometry should be DisplayMesh3D instead of DisplayFace3D.")] = False,
        hide_color_by: Annotated[bool, Field(description="Hide colored model context by default.")] = True,
        grid_data_display_mode: Annotated[str, Field(description="Result display mode or result metric hint.")] = "Surface",
        grid_index: Annotated[int | None, Field(description="Optional Agent index hint. Ignored.")] = None,
        active_grid_data: Annotated[str | None, Field(description="Optional active grid data folder name.")] = None,
        name: Annotated[str, Field(description="VisualizationSet identifier and artifact name.")] = "radiance_grid_result",
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict.")] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from Radiance grid results through an alias."""
        if grid_data_path is None and grid_results_path is not None:
            grid_data_path = grid_results_path
        if grid_data_display_mode.strip().lower() in {
            "illuminance",
            "irradiance",
            "radiation",
            "luminance",
        }:
            grid_data_display_mode = "Surface"
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            grid_data_path=grid_data_path,
            output_name=output_name,
            result_subfolder=result_subfolder,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            grid_data_display_mode=grid_data_display_mode,
            active_grid_data=active_grid_data,
            name=name,
            return_visualization_set=return_visualization_set,
        )
