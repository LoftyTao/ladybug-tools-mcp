"""Edit 2D Legend Parameter MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.legend import edit_2d_legend_parameter as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_edit_2d_legend_parameter tool.'

    @mcp.tool(
        name='edit_2d_legend_parameter',
        description=(
            "Edit a Ladybug Display 2D legend parameter payload for "
            "VisualizationSet chart and model exports. Pass object_dict from "
            "visualization_create_2d_legend_parameter or an existing legend "
            "dict. This edits display settings only; it does not save a Garden "
            "target, update a VisualizationSet, or rerun analysis. Returns "
            "object_dict and summary_view."
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
    def edit_2d_legend_parameter(
        legend_parameter: Annotated[
            dict[str, Any],
            Field(
                description='2D LegendParameters dictionary returned by visualization_create_2d_legend_parameter.'
            ),
        ],
        title: Annotated[
            str | None, Field(description="Optional updated legend title.")
        ] = None,
        segment_count: Annotated[
            int | None, Field(description="Optional updated legend segment count.")
        ] = None,
        decimal_count: Annotated[
            int | None, Field(description="Optional updated decimal count.")
        ] = None,
        minimum: Annotated[
            float | None, Field(description="Optional updated legend minimum value.")
        ] = None,
        maximum: Annotated[
            float | None, Field(description="Optional updated legend maximum value.")
        ] = None,
        position_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional updated 2D position dict with originx and originy."
            ),
        ] = None,
        dimensions_2d: Annotated[
            dict[str, Any] | None,
            Field(description="Optional updated 2D dimensions dict."),
        ] = None,
        orientation: Annotated[
            str | None,
            Field(description="Optional updated orientation: vertical or horizontal."),
        ] = None,
        color_set: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional updated Ladybug colorset name or dict with name/colors."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a 2D legend parameter dict."""
        return service(
            legend_parameter=legend_parameter,
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
