"""Radiance glare metric summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.metrics import summarize_radiance_glare_metrics as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_summarize_glare_metrics tool.'

    @mcp.tool(
        name="summarize_glare_metrics",
        description=(
            "Summarize annual Radiance glare metrics from a completed glare or "
            "view run into compact DGP and visual-discomfort statistics. Use "
            "after radiance_poll_simulation and output listing confirm results "
            "exist. This reads glare metric artifacts; it does not run view "
            "recipes or convert HDR images. Returns target, summary_view, "
            "metrics, and report."
        ),
        tags={
            "radiance",
            "glare",
            "metrics",
            "result",
        },
        timeout=60,
    )
    def summarize_radiance_glare_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with DGP/glare result outputs. Poll the run before summarizing metrics."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional completed glare-capable Radiance run identifier."),
        ] = None,
        view_identifier: Annotated[
            str | None,
            Field(description="Optional view identifier for report provenance."),
        ] = None,
        dgp_threshold: Annotated[
            float,
            Field(
                description="DGP threshold for exceedance summary. Pass/fail still depends on user/project criteria."
            ),
        ] = 0.4,
        save_report: Annotated[
            bool,
            Field(description="Save a compact JSON glare report artifact in the Garden and return a target."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Return raw DGP values. Keep false for compact report handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Summarize DGP/glare metrics."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            view_identifier=view_identifier,
            dgp_threshold=dgp_threshold,
            save_report=save_report,
            include_values=include_values,
        )
