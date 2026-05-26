"""Dragonfly comparison VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.display import (
    dragonfly_models_to_comparison_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_models_to_comparison_visualization_set tool."""

    @mcp.tool(
        name="models_to_comparison_visualization_set",
        description=(
            "Create a Ladybug Display comparison VisualizationSet for two Garden "
            "Dragonfly models using Dragonfly Display model_comparison_to_vis_set. If "
            "Web View mode is active, this tool refreshes the demo panel; call "
            "visualization_set_to_vtkjs only when the user asks for a saved vtk.js asset. "
            "Returns visualization_set_target when saved and leaves both Dragonfly "
            "source models unchanged."
        ),
        tags={"dragonfly", "visualization-set", "compare", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_models_to_comparison_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        base_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Model target for the base comparison model."),
        ] = None,
        incoming_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Model target for the incoming comparison model."),
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
            Field(description="Whether to return the VisualizationSet body. False saves and returns a compact visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly comparison VisualizationSet."""
        if base_model_target is None or incoming_model_target is None:
            raise ValueError(
                "dragonfly_models_to_comparison_visualization_set requires "
                "base_model_target and incoming_model_target."
            )
        return service(
            garden_root=garden_root,
            base_model_target=base_model_target,
            incoming_model_target=incoming_model_target,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )
