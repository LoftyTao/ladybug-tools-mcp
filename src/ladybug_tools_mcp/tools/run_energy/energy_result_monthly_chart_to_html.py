"""Energy result monthly chart HTML MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import (
    energy_result_monthly_chart_to_html as service,
)


def register(mcp: FastMCP) -> None:
    """Register the energy_result_monthly_chart_to_html tool."""

    @mcp.tool(
        name="energy_result_monthly_chart_to_html",
        description="Compatibility path: create a Garden HTML artifact directly from one or more EnergyPlus SQL DataCollections using Ladybug MonthlyChart / monthly chart. Prefer read_energy_result_data with save_data_collections=true for each output_name, then data_collection_monthly_chart_to_visualization_set with series[].data_collection_target and return_visualization_set=false, then visualization_set_to_html with visualization_set_target. Keep this direct tool for legacy/debug clients that need one Energy-owned chart-to-HTML call for hourly, annual monthly, daily or monthly aggregation, monthly-per-hour patterns, and multi-series result comparisons. Each series item uses output_name, optional collection_index, and optional label; the label is written into the DataCollection header metadata for the chart legend.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "result",
            "visualize",
            "monthly-chart",
            "line-chart",
            "daily-chart",
            "monthly-per-hour",
            "data-collection",
            "sql",
            "html",
            "artifact",
            "legend",
            "metadata",
            "write",
            "safe",
        },
        timeout=90,
    )
    def energy_result_monthly_chart_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires output_name and may include collection_index, run_period_index, and label. The label is written to DataCollection header metadata for the legend."
            ),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional energy_run target returned by start_energy_run or run_energy."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, hourly, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour."
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
            Field(
                description="Whether cumulative series should be stacked by MonthlyChart."
            ),
        ] = False,
        percentile: Annotated[
            float,
            Field(
                description="Percentile spread used by MonthlyChart for hourly data."
            ),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(
                description="Whether month labels are replaced with time-of-day marks."
            ),
        ] = False,
        name: Annotated[
            str,
            Field(description="HTML artifact file name without extension."),
        ] = "energy_result_monthly_chart",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/energy/results/html",
    ) -> dict[str, Any]:
        """Export Energy result DataCollections to a MonthlyChart HTML artifact."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            series=series,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            name=name,
            output_subdir=output_subdir,
        )
