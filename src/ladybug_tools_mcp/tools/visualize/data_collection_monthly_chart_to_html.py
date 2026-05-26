"""DataCollection MonthlyChart HTML MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.datacollection import (
    data_collection_monthly_chart_to_html as service,
)


def register(mcp: FastMCP) -> None:
    'Register the visualization_data_collection_monthly_chart_to_html tool.'

    @mcp.tool(
        name='data_collection_monthly_chart_to_html',
        description=(
            "Create a Garden HTML artifact from one or more Ladybug "
            "DataCollections using Ladybug MonthlyChart. Use series items with "
            "data_collection_target from Garden-backed upstream tools for "
            "schedule, weather, comfort, energy result, daily, monthly, or "
            "monthly-per-hour comparisons. Each series item uses "
            "data_collection or data_collection_target and optional label. "
            "This exports a chart artifact; it does not read SQL, EPW, or "
            "Radiance result folders."
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "artifact",
            "monthly-chart",
        },
        timeout=90,
    )
    def data_collection_monthly_chart_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires exactly one of data_collection, a Ladybug DataCollection dict, or data_collection_target, a ladybug_data_collection Garden target; may include label for the legend."
            ),
        ],
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour."
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
            Field(description="MonthlyChart HTML artifact file name without extension."),
        ] = "data_collection_monthly_chart",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/visualization/datacollections/html",
    ) -> dict[str, Any]:
        """Export Ladybug DataCollections to a MonthlyChart HTML artifact."""
        return service(
            garden_root=garden_root,
            series=series,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            output_subdir=output_subdir,
        )
