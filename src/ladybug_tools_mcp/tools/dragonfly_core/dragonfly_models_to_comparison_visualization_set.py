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
        name="dragonfly_models_to_comparison_visualization_set",
        description="Create a Ladybug Display comparison VisualizationSet for two Garden Dragonfly models using Dragonfly Display model_comparison_to_vis_set. If Web View mode is active, this tool automatically refreshes the demo panel; call visualization_set_to_vtkjs only when the user explicitly asks for a saved vtk.js asset.",
        tags={"dragonfly-core", "dragonfly-display", "visualization-set", "garden-mode", "compare", "visualize", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_models_to_comparison_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        base_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly model target for the base model."),
        ] = None,
        incoming_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly model target for the incoming model."),
        ] = None,
        source_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for base_model_target."),
        ] = None,
        target_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for incoming_model_target."),
        ] = None,
        model_a_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for base_model_target."),
        ] = None,
        model_b_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for incoming_model_target."),
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
            Field(description="Dragonfly Display merge_method. Use None for no merging."),
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
            Field(description="Whether to return the VisualizationSet body. False saves and returns a target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly comparison VisualizationSet."""
        base_model_target = base_model_target or source_model_target or model_a_target
        incoming_model_target = (
            incoming_model_target or target_model_target or model_b_target
        )
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
