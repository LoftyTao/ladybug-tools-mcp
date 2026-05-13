"""Read Fairyfly THERM U-Factor result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.results import read_fairyfly_u_factor_result as service


def register(mcp: FastMCP) -> None:
    """Register the read_fairyfly_u_factor_result tool."""

    @mcp.tool(
        name="read_fairyfly_u_factor_result",
        description=(
            "Read U-Factor summaries from a completed Fairyfly THERM THMZ file. "
            "Use this after assigning U-Factor tags and running THERM. If results "
            "are missing, returns no_results with a tag/runtime diagnostic."
        ),
        tags={
            "fairyfly",
            "therm",
            "result",
            "u-factor",
            "2d-heat-transfer",
            "garden-mode",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_u_factor_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional fairyfly_thmz target returned by write_fairyfly_model_to_thmz."),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional fairyfly_therm_run target returned by start_fairyfly_therm_run."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Fairyfly THERM U-Factor result summaries."""
        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
        )
