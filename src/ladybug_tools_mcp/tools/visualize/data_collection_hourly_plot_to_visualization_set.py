"""DataCollection HourlyPlot VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.datacollection import (
    data_collection_hourly_plot_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the data_collection_hourly_plot_to_visualization_set tool."""

    @mcp.tool(
        name="data_collection_hourly_plot_to_visualization_set",
        description="Generic visualize path: create a Ladybug Display VisualizationSet hourly plot from one hourly Ladybug DataCollection using Ladybug HourlyPlot. Use this for hourly energy result data, schedules, weather, comfort, or other time-series data after an upstream tool returns a ladybug_data_collection target. Preferred Agent path is garden_root plus data_collection_target from read_energy_result_data or another upstream tool and return_visualization_set=false, returning a compact visualization_set_target for visualization_set_to_html/svg instead of moving a large VisualizationSet dict. Direct data_collection dict input remains available for payload/debug workflows.",
        tags={
            "visualize",
            "generic-visualize",
            "data-collection",
            "data-collection-target",
            "hourly-plot",
            "hourly-energy-result",
            "timeseries",
            "schedule-data",
            "weather-data",
            "energy-result-data",
            "energy-result-visualization",
            "visualization-set",
            "target",
            "safe",
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
                description="Optional ladybug_data_collection target returned by an upstream tool such as create_schedule_ruleset with garden_root and return_data=false."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root required when data_collection_target is provided."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "data_collection_hourly_plot",
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
            name=name,
            return_visualization_set=return_visualization_set,
        )
