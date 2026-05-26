"""Read Fairyfly THERM U-Factor result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.results import read_fairyfly_u_factor_result as service


def register(mcp: FastMCP) -> None:
    'Register the therm_read_u_factor tool.'

    @mcp.tool(
        name="read_u_factor",
        description=(
            "Read U-Factor summaries from a Fairyfly THERM THMZ file. Use this "
            "after assigning U-Factor tags, running THERM, and polling "
            "therm_poll_simulation before reading from a run_target. If results "
            "are missing, returns no_results with a tag/runtime diagnostic. Returns "
            "u_factor_result_target, summary_view, and report when values exist; use "
            "therm_read_result for temperature or heat-flux statistics."
        ),
        tags={"fairyfly", "therm", "u-factor", "result", "summary"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_u_factor_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by therm_write_model_to_thmz.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by therm_start_simulation. Poll before reading U-factor results.'),
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
