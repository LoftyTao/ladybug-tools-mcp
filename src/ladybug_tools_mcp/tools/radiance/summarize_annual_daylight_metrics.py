"""Annual daylight metric summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.metrics import summarize_annual_daylight_metrics as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_summarize_annual_daylight_metrics tool.'

    @mcp.tool(
        name='summarize_annual_daylight_metrics',
        description=(
            "Summarize completed Honeybee Radiance annual daylight metrics such "
            "as sDA, ASE, DA, CDA, UDI, daylight autonomy, annual sunlight "
            "exposure, and too-much-sun risk into a compact Garden-backed "
            "report. Use after a completed annual daylight run. This reads "
            "Radiance daylight metric artifacts; it does not run recipes or "
            "evaluate EnergyPlus daylighting controls. Pass/fail "
            "interpretation requires project or rating-system thresholds."
        ),
        tags={
            "metrics",
            "radiance",
            "result",
        },
        timeout=60,
    )
    def summarize_annual_daylight_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed annual-daylight radiance_run target. Poll the run before summarizing metrics."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(
                description="Optional completed annual daylight run identifier when run_target is omitted."
            ),
        ] = None,
        grid_identifier: Annotated[
            str | None,
            Field(description="Optional grid identifier for report provenance and future filtering."),
        ] = None,
        metrics: Annotated[
            list[str] | None,
            Field(
                description="Optional metrics to summarize, for example ['sda', 'ase', 'da', 'udi']."
            ),
        ] = None,
        save_report: Annotated[
            bool,
            Field(description="Save a compact JSON report artifact in the Garden and return a target."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Return raw metric values. Keep false for compact report handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Summarize annual daylight metrics."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            grid_identifier=grid_identifier,
            metrics=metrics,
            save_report=save_report,
            include_values=include_values,
        )
