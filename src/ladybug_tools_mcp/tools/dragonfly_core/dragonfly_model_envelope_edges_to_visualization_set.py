"""Dragonfly envelope-edge VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.display import (
    dragonfly_model_envelope_edges_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_model_envelope_edges_to_visualization_set tool."""

    @mcp.tool(
        name="dragonfly_model_envelope_edges_to_visualization_set",
        description="Create a Ladybug Display VisualizationSet showing Dragonfly model envelope edges using Dragonfly Display model_envelope_edges_to_vis_set. If Web View mode is active, this tool automatically refreshes the demo panel; call visualization_set_to_vtkjs only when the user explicitly asks for a saved vtk.js asset. If the SDK edge view is unavailable for the model geometry, this tool returns report.status=degraded and a wireframe model VisualizationSet fallback target instead of raising an error or inviting repeated retries.",
        tags={
            "dragonfly-core",
            "dragonfly-display",
            "visualization-set",
            "garden-mode",
            "visualize",
            "edge-preview",
            "wireframe-fallback",
            "web-3d-source",
            "vtkjs-source",
            "geometry-asset",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_model_envelope_edges_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        coplanar_type: Annotated[
            str,
            Field(description="Dragonfly Display coplanar_type: None, FloorPlatesOnly, or All."),
        ] = "FloorPlatesOnly",
        mullion_thickness: Annotated[
            float | None,
            Field(description="Optional mullion thickness threshold."),
        ] = None,
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
        """Create a Dragonfly envelope-edge VisualizationSet."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            coplanar_type=coplanar_type,
            mullion_thickness=mullion_thickness,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )
