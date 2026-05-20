"""Radiance grid result VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_grid_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_grid_result_to_visualization_set tool."""

    @mcp.tool(
        name="radiance_grid_result_to_visualization_set",
        description="Create a Ladybug Display VisualizationSet target from Radiance SensorGrid result folders using honeybee_display.model_to_vis_set(grid_data_path=...). This stops at VisualizationSet output; use existing visualization_set_to_html or visualization_set_to_svg tools for file export.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "postprocess",
            "sensor-grid",
            "grid",
            "results",
            "visualization-set",
            "visualize",
            "write",
            "safe",
        },
        timeout=60,
    )
    def radiance_grid_result_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with SensorGrid result outputs."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        grid_data_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative folder containing grids_info.json. Use instead of run_target/run_id."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(description="Optional run output name to use. Defaults to results when resolving from a run."),
        ] = None,
        result_subfolder: Annotated[
            str | None,
            Field(description="Optional subfolder inside the selected output, for example da or cumulative_radiation."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional model target override. Defaults to the model_target recorded on the run."),
        ] = None,
        color_by: Annotated[
            str | None,
            Field(description="Model context coloring: type, boundary_condition, or none. Use none for result-first views."),
        ] = "none",
        include_wireframe: Annotated[
            bool,
            Field(description="Include model wireframe context in the VisualizationSet."),
        ] = True,
        use_mesh: Annotated[
            bool,
            Field(description="Whether model context geometry should be DisplayMesh3D instead of DisplayFace3D."),
        ] = False,
        hide_color_by: Annotated[
            bool,
            Field(description="Hide colored model context by default when result data is primary."),
        ] = True,
        grid_data_display_mode: Annotated[
            str,
            Field(description="Result display mode: Surface, SurfaceWithEdges, Wireframe, or Points."),
        ] = "Surface",
        active_grid_data: Annotated[
            str | None,
            Field(description="Optional active grid data folder name when grid_data_path contains multiple datasets."),
        ] = None,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and artifact name."),
        ] = "radiance_grid_result",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. Set false for compact Agent target handoff."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from Radiance grid results."""
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
