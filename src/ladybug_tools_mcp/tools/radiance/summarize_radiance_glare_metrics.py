"""Radiance glare metric summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.metrics import summarize_radiance_glare_metrics as service


def register(mcp: FastMCP) -> None:
    """Register the summarize_radiance_glare_metrics tool."""

    @mcp.tool(
        name="summarize_radiance_glare_metrics",
        description=(
            "Summarize DGP / glare metrics from completed supported Radiance glare "
            "outputs. Use this for visual discomfort, annual glare, too-bright "
            "view, and DGP result summaries. This tool does not convert HDR, GIF, "
            "or falsecolor brightness into DGP; if only images exist it returns a "
            "blocked diagnostic."
        ),
        tags={
            "honeybee-radiance",
            "radiance",
            "glare",
            "dgp",
            "annual-glare",
            "visual-discomfort",
            "too-bright",
            "postprocess",
            "metrics",
            "compact",
            "safe",
        },
        timeout=60,
    )
    def summarize_radiance_glare_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with DGP/glare result outputs."),
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
            Field(description="Return raw DGP values. Keep false for compact Agent use."),
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
