"""DataCollection MonthlyChart VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.datacollection import (
    data_collection_monthly_chart_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the visualization_data_collection_monthly_chart_to_visualization_set tool.'

    @mcp.tool(
        name='data_collection_monthly_chart_to_visualization_set',
        description=(
            "Create a Ladybug Display VisualizationSet monthly chart from one "
            "or more Ladybug DataCollection targets such as EnergyPlus result "
            "or EPW weather data already saved in the Garden. Each series uses "
            "data_collection_target or direct data_collection plus optional "
            "label metadata. This charts existing DataCollections; it does not "
            "read SQL, EPW, or Radiance folders. Returns target, "
            "visualization_set_target, summary_view, persistence_receipt, and "
            "report for vtkjs/html export."
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "monthly-chart",
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
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
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
            Field(
                description="Whether month labels are replaced with time-of-day marks. Automatically enabled for monthly_per_hour and total_monthly_per_hour charts."
            ),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart X dimension for each month. Defaults to 10, or 50 for monthly_per_hour/total_monthly_per_hour charts."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart Y dimension for the chart height. Defaults to 40."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="MonthlyChart VisualizationSet identifier and display name."),
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
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            return_visualization_set=return_visualization_set,
        )
