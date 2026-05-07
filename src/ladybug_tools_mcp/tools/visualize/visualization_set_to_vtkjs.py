"""Visualization Set To vtkjs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.artifacts import visualization_set_to_vtkjs as service


def register(mcp: FastMCP) -> None:
    """Register the visualization_set_to_vtkjs tool."""

    @mcp.tool(
        name="visualization_set_to_vtkjs",
        description="Export a Ladybug Display VisualizationSet to a vtkjs artifact inside a Garden and record it in garden.json artifacts. This is the SDK-native geometry package for downstream React, vtk.js, and Remotion workflows. Preferred Agent path is visualization_set_target from an upstream visualize tool; direct visualization_set dict input remains available for payload/debug workflows.",
        tags={
            "visualize",
            "garden-mode",
            "artifact",
            "export",
            "write",
            "safe",
            "vtkjs",
        },
        timeout=60,
    )
    def visualization_set_to_vtkjs(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional VisualizationSet dictionary from a visualize tool. Use visualization_set_target instead for Agent token-saving Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with garden_root and return_visualization_set=false."
            ),
        ] = None,
        name: Annotated[
            str, Field(description="vtkjs artifact file name without extension.")
        ] = "visualization_set",
        visualization_set_identifier: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the vtkjs artifact file name."
            ),
        ] = None,
        visualization_set_display_name: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the vtkjs artifact file name."
            ),
        ] = None,
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/vtkjs",
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden vtkjs artifact."""
        if name == "visualization_set" and visualization_set_identifier:
            name = visualization_set_identifier
        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
        )
