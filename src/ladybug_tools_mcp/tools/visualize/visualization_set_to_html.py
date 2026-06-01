"""Visualization Set To HTML MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.artifacts import visualization_set_to_html as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_set_to_html tool.'

    @mcp.tool(
        name="set_to_html",
        description=(
            "Export a Ladybug Display VisualizationSet to a standalone "
            "interactive HTML page artifact inside a Garden and record it in "
            "garden.json artifacts. Use this when the user asks for an HTML "
            "page, report page, or browser-openable preview file. Preferred "
            "Agent path is visualization_set_target from an upstream visualize "
            "tool. For Web 3D geometry packages, vtk.js assets, FastMCP App "
            "viewer assets, Remotion assets, or reusable geometry assets, use "
            "visualization_set_to_vtkjs. This exporter does not create or "
            "modify the VisualizationSet source data."
        ),
        tags={
            "visualization-set",
            "export",
            "artifact",
        },
        timeout=60,
    )
    def visualization_set_to_html(
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
            str, Field(description="HTML artifact file name without extension.")
        ] = "visualization_set",
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/html",
        open: Annotated[
            bool, Field(description="Whether to open the HTML artifact after export.")
        ] = False,
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden HTML artifact."""
        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
            open=open,
        )
