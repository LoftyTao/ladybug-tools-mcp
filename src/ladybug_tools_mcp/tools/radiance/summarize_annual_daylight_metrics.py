"""Annual daylight metric summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.metrics import summarize_annual_daylight_metrics as service


def register(mcp: FastMCP) -> None:
    """Register the summarize_annual_daylight_metrics tool."""

    @mcp.tool(
        name="summarize_annual_daylight_metrics",
        description=(
            "Summarize completed Honeybee Radiance annual daylight metrics such as "
            "sDA, ASE, DA, CDA, UDI, daylight autonomy, annual sunlight exposure, "
            "and too-much-sun risk into a compact Garden-backed report. Use this "
            "for Radiance daylight quality metrics, not EnergyPlus daylighting "
            "control or lighting energy. Values are calculable, but pass/fail "
            "interpretation requires user, project, or rating-system thresholds."
        ),
        tags={
            "honeybee-radiance",
            "radiance",
            "annual-daylight",
            "daylight-autonomy",
            "sda",
            "ase",
            "udi",
            "too-much-sun",
            "metrics",
            "postprocess",
            "compact",
            "safe",
        },
        timeout=60,
    )
    def summarize_annual_daylight_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed annual daylight radiance_run target."),
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
            Field(description="Return raw metric values. Keep false for compact Agent use."),
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
