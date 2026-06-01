"""Create Dragonfly Model VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.display import (
    dragonfly_model_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_model_to_visualization_set tool."""

    @mcp.tool(
        name="model_to_visualization_set",
        description=(
            "Create a Ladybug Display VisualizationSet from a Garden Dragonfly model "
            "using Dragonfly Display for web 3D, FastMCP App viewer, Remotion, and geometry "
            "asset workflows. Can return the VisualizationSet body or save it as a "
            "Garden visualization_set target with return_visualization_set=false. If "
            "Web View mode is active, this tool refreshes the demo panel; call "
            "visualization_set_to_vtkjs only when the user asks for a saved vtk.js asset. "
            "This tool has no object_type parameter and does not edit Dragonfly geometry."
        ),
        tags={"dragonfly", "visualization-set", "model", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_model_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Whether to display Dragonfly story multipliers."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Whether to exclude Dragonfly plenum Room2Ds."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Whether to solve interior story ceiling adjacencies."),
        ] = False,
        merge_method: Annotated[
            str,
            Field(description="Dragonfly Display merge_method. Use the string None for no merging."),
        ] = "None",
        color_by: Annotated[
            str | None,
            Field(description="Dragonfly Display color_by value: type, boundary_condition, or None."),
        ] = "type",
        include_wireframe: Annotated[
            bool,
            Field(description="Whether to include model wireframe geometry."),
        ] = True,
        use_mesh: Annotated[
            bool,
            Field(description="Whether color geometry should use DisplayMesh3D."),
        ] = True,
        hide_color_by: Annotated[
            bool,
            Field(description="Whether color-by geometry is hidden by default."),
        ] = False,
        grid_display_mode: Annotated[
            str,
            Field(description="SensorGrid display mode for Dragonfly Display."),
        ] = "Default",
        hide_grid: Annotated[
            bool,
            Field(description="Whether SensorGrid geometry is hidden by default."),
        ] = False,
        reset_coordinates: Annotated[
            bool,
            Field(description="Whether to reset model coordinates around the origin."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return a compact visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly model VisualizationSet."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            color_by=color_by,
            include_wireframe=include_wireframe,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            grid_display_mode=grid_display_mode,
            hide_grid=hide_grid,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )
