"""Energy result monthly chart HTML MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import (
    energy_result_monthly_chart_to_html as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energyplus_result_monthly_chart_to_html tool.'

    @mcp.tool(
        name="result_monthly_chart_to_html",
        description="Create a ready-to-open Garden HTML artifact from one or more EnergyPlus SQL DataCollections using Ladybug MonthlyChart. Each series item uses output_name plus optional collection_index, run_period_index, and label metadata. Returns artifact_receipt, summary_view.artifact, summary_view.series, and report; pass artifact_receipt.artifact_path or summary_view.artifact.path to preview/export flows.",
        tags={
            "energy",
            "result",
            "sql",
            "visualize",
            "monthly-chart",
            "artifact",
        },
        timeout=90,
    )
    def energy_result_monthly_chart_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
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
                description='Energy run target returned by energyplus_start_simulation; pass run_target for polling unless you provide run_id.'
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
