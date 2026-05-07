"""DataCollection MonthlyChart VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.datacollection import (
    data_collection_monthly_chart_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the data_collection_monthly_chart_to_visualization_set tool."""

    @mcp.tool(
        name="data_collection_monthly_chart_to_visualization_set",
        description="Generic visualize path: create a Ladybug Display VisualizationSet from one or more Ladybug DataCollections using Ladybug MonthlyChart. Use this for energy result charts, schedule charts, weather charts, daily lines, monthly average lines, monthly per hour heatmaps/lines, total monthly summaries, and multi-series comparisons. Preferred Agent path is garden_root plus series items with data_collection_target from read_energy_result_data or another upstream tool and return_visualization_set=false, returning a compact visualization_set_target for visualization_set_to_html/svg instead of moving a large VisualizationSet dict. Each series item uses exactly one of data_collection or data_collection_target, not both, and may include label; the label is written into DataCollection header metadata as legend metadata for the chart legend.",
        tags={
            "visualize",
            "generic-visualize",
            "data-collection",
            "data-collection-target",
            "monthly-chart",
            "line-chart",
            "daily-chart",
            "monthly-average",
            "monthly-per-hour",
            "total-monthly",
            "timeseries",
            "schedule-data",
            "weather-data",
            "energy-result-data",
            "energy-result-visualization",
            "visualization-set",
            "target",
            "legend",
            "metadata",
            "safe",
        },
        timeout=60,
    )
    def data_collection_monthly_chart_to_visualization_set(
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires exactly one of data_collection or data_collection_target, not both. data_collection is a Ladybug DataCollection dict; data_collection_target is a ladybug_data_collection Garden target. May include label for the legend."
            ),
        ],
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root required when any series item uses data_collection_target."
            ),
        ] = None,
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, hourly, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour. Use monthly for monthly average lines and monthly_per_hour for monthly average by hour patterns."
            ),
        ] = "as_is",
        chart_title: Annotated[
            str | None,
            Field(description="Optional global title for the chart."),
        ] = None,
        y_axis_title: Annotated[
            str | None,
            Field(description="Optional Y-axis title for the chart."),
        ] = None,
        stack: Annotated[
            bool,
            Field(description="Whether cumulative series should be stacked by MonthlyChart."),
        ] = False,
        percentile: Annotated[
            float,
            Field(description="Percentile spread used by MonthlyChart for hourly data."),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(description="Whether month labels are replaced with time-of-day marks."),
        ] = False,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "data_collection_monthly_chart",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to pass visualization_set_target downstream without a large object handoff."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a MonthlyChart VisualizationSet from DataCollections."""
        return service(
            series=series,
            garden_root=garden_root,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            name=name,
            return_visualization_set=return_visualization_set,
        )
