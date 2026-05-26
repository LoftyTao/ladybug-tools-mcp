"""Create 2D Legend Parameter MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.legend import create_2d_legend_parameter as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_create_2d_legend_parameter tool.'

    @mcp.tool(
        name='create_2d_legend_parameter',
        description=(
            "Create a Ladybug Display 2D legend parameter payload for "
            "VisualizationSet chart and model exports. Use the returned "
            "object_dict in visualization or chart tools when a custom legend "
            "is needed. This is a display settings object, not a saved Garden "
            "target or analysis result. Returns object_dict and summary_view."
        ),
        tags={
            "visualization-set",
            "visualize",
            "author",
            "legend",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def create_2d_legend_parameter(
        title: Annotated[
            str | None, Field(description="Optional 2D legend title.")
        ] = None,
        segment_count: Annotated[
            int | None, Field(description="Optional legend segment count.")
        ] = None,
        decimal_count: Annotated[
            int | None, Field(description="Optional decimal count for legend labels.")
        ] = None,
        minimum: Annotated[
            float | None, Field(description="Optional legend minimum value.")
        ] = None,
        maximum: Annotated[
            float | None, Field(description="Optional legend maximum value.")
        ] = None,
        position_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional 2D position dict with originx and originy, such as 5% or 20px."
            ),
        ] = None,
        dimensions_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional 2D dimensions dict with segment_height, segment_width, and text_height, such as 24px."
            ),
        ] = None,
        orientation: Annotated[
            str, Field(description="Legend orientation: vertical or horizontal.")
        ] = "vertical",
        color_set: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional Ladybug colorset name or dict with name/colors."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a 2D legend parameter dict."""
        return service(
            title=title,
            segment_count=segment_count,
            decimal_count=decimal_count,
            minimum=minimum,
            maximum=maximum,
            position_2d=position_2d,
            dimensions_2d=dimensions_2d,
            orientation=orientation,
            color_set=color_set,
        )
