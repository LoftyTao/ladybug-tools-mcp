"""Create Fairyfly Model VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.display import fairyfly_model_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    'Register the therm_model_to_visualization_set tool.'

    @mcp.tool(
        name="model_to_visualization_set",
        description=(
            "Create a Ladybug Display VisualizationSet from a Garden Fairyfly model. "
            "Set return_visualization_set=false to save a compact visualization_set_target "
            "for visualization_set_to_html, SVG, or vtk.js export. This visualizes the "
            "2D section geometry and does not read THERM result arrays."
        ),
        tags={"fairyfly", "therm", "visualization-set", "model", "visualize", "preview"},
        timeout=20,
    )
    def fairyfly_model_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually therm_create_model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(description="Model coloring mode. Supported: material, none."),
        ] = "material",
        include_boundaries: Annotated[
            bool,
            Field(description="Whether to include Fairyfly Boundary line geometry."),
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and artifact name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. False saves and returns a compact visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Fairyfly model VisualizationSet."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            color_by=color_by,
            include_boundaries=include_boundaries,
            name=name,
            return_visualization_set=return_visualization_set,
        )
