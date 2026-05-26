"""DataCollection HourlyPlot VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.datacollection import (
    data_collection_hourly_plot_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the visualization_data_collection_hourly_plot_to_visualization_set tool.'

    @mcp.tool(
        name='data_collection_hourly_plot_to_visualization_set',
        description=(
            "Create a Ladybug Display VisualizationSet hourly plot from one "
            "hourly Ladybug DataCollection using Ladybug HourlyPlot. Use this "
            "for hourly energy result data, schedules, weather, comfort, or "
            "other time-series data after an upstream tool returns a "
            "ladybug_data_collection target. Preferred Agent path is "
            "garden_root plus data_collection_target and "
            "return_visualization_set=false, returning a compact "
            "visualization_set_target for exporters. This charts an existing "
            "DataCollection; it does not query SQL, EPW, or Radiance folders."
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "hourly-plot",
        },
        timeout=60,
    )
    def data_collection_hourly_plot_to_visualization_set(
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug hourly DataCollection dictionary. Use data_collection_target instead for Agent token-saving Garden workflows."
            ),
        ] = None,
        data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional ladybug_data_collection target returned by an upstream tool such as energy_create_schedule_ruleset with garden_root and return_data=false.'
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="HourlyPlot VisualizationSet identifier and display name."),
        ] = "data_collection_hourly_plot",
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK HourlyPlot X dimension for each day/cell column. Defaults to 1."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK HourlyPlot Y dimension for each hour/cell row. Defaults to 4."
            ),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to pass visualization_set_target downstream without a large object handoff."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create an HourlyPlot VisualizationSet from a DataCollection."""
        return service(
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            garden_root=garden_root,
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            return_visualization_set=return_visualization_set,
        )
