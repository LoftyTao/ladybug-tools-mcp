"""Radiance grid result VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_grid_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_grid_result_to_visualization_set tool."""

    @mcp.tool(
        name="grid_result_to_visualization_set",
        description=(
            "Create a Ladybug Display VisualizationSet target from Radiance "
            "SensorGrid result folders using "
            "honeybee_display.model_to_vis_set(grid_data_path=...). This "
            "converts existing grid results into a VisualizationSet; it does "
            "not start a Radiance recipe or export HTML/SVG/vtk.js files."
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "result",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def radiance_grid_result_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with SensorGrid result outputs. Poll the run before converting result data."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed grid or matrix run when run_target is not supplied."),
        ] = None,
        grid_data_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative folder containing grids_info.json for direct result-folder conversion."),
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
            Field(description="Return the full VisualizationSet dict. Set false to save a compact Garden visualization_set_target for export tools."),
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
