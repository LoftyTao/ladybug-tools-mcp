"""Visualization Set To vtkjs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.artifacts import visualization_set_to_vtkjs as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_set_to_vtkjs tool.'

    @mcp.tool(
        name="set_to_vtkjs",
        description=(
            "Export a Ladybug Display VisualizationSet to a persistent .vtkjs "
            "artifact inside a Garden and record it in garden.json artifacts. "
            "Use this when the user asks for a saved vtk.js or Web 3D asset "
            "for React, vtk.js, WebGL, Remotion, or reusable geometry "
            "workflows. It does not export GLB/VTP and has no file_format "
            "parameter. Preferred Agent path is visualization_set_target from "
            "an upstream visualize tool; the parameter name is exactly "
            "visualization_set_target. This exporter does not create or "
            "modify the VisualizationSet source data."
        ),
        tags={
            "visualization-set",
            "vtkjs",
            "export",
            "artifact",
        },
        timeout=60,
    )
    def visualization_set_to_vtkjs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct VisualizationSet dictionary from a visualize tool. Prefer visualization_set_target for compact Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with return_visualization_set=false."
            ),
        ] = None,
        name: Annotated[
            str, Field(description="vtkjs artifact file name without extension.")
        ] = "visualization_set",
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/vtkjs",
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden vtkjs artifact."""
        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
        )
