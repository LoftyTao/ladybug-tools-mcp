"""Compose model-context and analysis VisualizationSet targets."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.honeybee import compose_model_analysis_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the compose_model_analysis_visualization_set tool."""

    @mcp.tool(
        name="compose_model_analysis_visualization_set",
        description="Compose a Garden-backed model-context VisualizationSet target with an analysis-result VisualizationSet target, typically for overlays like model wireframe plus Radiance mesh results.",
        tags={"visualize", "visualization-set", "overlay", "compose", "write", "safe"},
        timeout=30,
    )
    def compose_model_analysis_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_context_target: Annotated[
            dict[str, Any],
            Field(description="VisualizationSet target for model context geometry."),
        ],
        analysis_visualization_set_target: Annotated[
            dict[str, Any],
            Field(description="VisualizationSet target for the analysis/result layer."),
        ],
        name: Annotated[
            str,
            Field(description="Output VisualizationSet identifier and artifact name."),
        ] = "model_analysis_overlay",
        units: Annotated[
            str | None,
            Field(description="Optional output units. If omitted, input units must match."),
        ] = None,
        exclude_context_geometry_identifiers: Annotated[
            list[str] | None,
            Field(description="Context geometry layer identifiers to omit, defaulting to Sensor_Grids."),
        ] = None,
        conflict_strategy: Annotated[
            str,
            Field(description="Geometry identifier conflict strategy: error or rename."),
        ] = "rename",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. Set false for compact target handoff."),
        ] = True,
    ) -> dict[str, Any]:
        """Compose model context with an analysis VisualizationSet and save it."""
        return service(
            garden_root=garden_root,
            model_context_target=model_context_target,
            analysis_visualization_set_target=analysis_visualization_set_target,
            name=name,
            units=units,
            exclude_context_geometry_identifiers=exclude_context_geometry_identifiers,
            conflict_strategy=conflict_strategy,
            return_visualization_set=return_visualization_set,
        )
