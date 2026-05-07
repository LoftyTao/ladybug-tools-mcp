"""Visualization Set To SVG MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.artifacts import visualization_set_to_svg as service


def register(mcp: FastMCP) -> None:
    """Register the visualization_set_to_svg tool."""

    @mcp.tool(
        name="visualization_set_to_svg",
        description="Export a Ladybug Display VisualizationSet to an SVG artifact inside a Garden and record it in garden.json artifacts. Preferred Agent path is visualization_set_target from an upstream visualize tool; direct visualization_set dict input remains available for payload/debug workflows.",
        tags={"visualize", "garden-mode", "artifact", "export", "write", "safe", "svg"},
        timeout=60,
    )
    def visualization_set_to_svg(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional VisualizationSet dictionary from a visualize or compose tool. Use visualization_set_target instead for Agent token-saving Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with garden_root and return_visualization_set=false."
            ),
        ] = None,
        width: Annotated[int, Field(description="SVG canvas width in pixels.")] = 1600,
        height: Annotated[int, Field(description="SVG canvas height in pixels.")] = 900,
        view: Annotated[
            str,
            Field(
                description="Projection view: Top, Left, Right, Front, Back, NE, NW, SE, or SW."
            ),
        ] = "Top",
        interactive: Annotated[
            bool, Field(description="Whether to preserve SVG hover interactivity.")
        ] = False,
        render_2d_legend: Annotated[
            bool, Field(description="Whether to render 2D legends in the SVG.")
        ] = True,
        render_3d_legend: Annotated[
            bool, Field(description="Whether to render 3D legends in the SVG.")
        ] = False,
        name: Annotated[
            str, Field(description="SVG artifact file name without extension.")
        ] = "visualization_set",
        visualization_set_identifier: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the SVG artifact file name."
            ),
        ] = None,
        visualization_set_display_name: Annotated[
            str | None,
            Field(
                description="Optional ignored compatibility hint from upstream VisualizationSet metadata. Use name for the SVG artifact file name."
            ),
        ] = None,
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/svg",
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden SVG artifact."""
        if name == "visualization_set" and visualization_set_identifier:
            name = visualization_set_identifier
        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            width=width,
            height=height,
            view=view,
            interactive=interactive,
            render_2d_legend=render_2d_legend,
            render_3d_legend=render_3d_legend,
            name=name,
            output_subdir=output_subdir,
        )
