"""Visualization Set To HTML MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.artifacts import visualization_set_to_html as service


def register(mcp: FastMCP) -> None:
    """Register the visualization_set_to_html tool."""

    @mcp.tool(
        name="visualization_set_to_html",
        description="Export a Ladybug Display VisualizationSet to a standalone interactive HTML page artifact inside a Garden and record it in garden.json artifacts. Use this when the user asks for an HTML page, report page, or browser-openable preview file. Preferred Agent path is visualization_set_target from an upstream visualize tool; direct visualization_set dict input remains available for payload/debug workflows. For Web 3D geometry packages, vtk.js assets, React viewer assets, Remotion assets, or reusable geometry assets, use visualization_set_to_vtkjs instead, not this HTML exporter.",
        tags={
            "visualize",
            "garden-mode",
            "artifact",
            "export",
            "html-page",
            "browser-preview",
            "not-vtkjs",
            "write",
            "safe",
        },
        timeout=60,
    )
    def visualization_set_to_html(
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
            str, Field(description="HTML artifact file name without extension.")
        ] = "visualization_set",
        visualization_set_identifier: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the HTML artifact file name."
            ),
        ] = None,
        visualization_set_display_name: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the HTML artifact file name."
            ),
        ] = None,
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/html",
        open: Annotated[
            bool, Field(description="Whether to open the HTML artifact after export.")
        ] = False,
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden HTML artifact."""
        if name == "visualization_set" and visualization_set_identifier:
            name = visualization_set_identifier
        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
            open=open,
        )
