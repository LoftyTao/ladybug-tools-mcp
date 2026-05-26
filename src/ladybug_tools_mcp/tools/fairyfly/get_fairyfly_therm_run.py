"""Get Fairyfly THERM run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import get_fairyfly_therm_run as service


def register(mcp: FastMCP) -> None:
    'Register the therm_poll_simulation tool.'

    @mcp.tool(
        name="poll_simulation",
        description=(
            "Get one Garden Fairyfly THERM run record by fairyfly_therm_run "
            "target or run_id. Use this after starting a THERM run to inspect "
            "runtime_status without returning large result data. Returns "
            "runtime_status, poll_next, summary_view, and report. Treat a "
            "failed runtime_status as requiring report review before reading THERM "
            "or U-factor results."
        ),
        tags={"fairyfly", "therm", "runtime", "poll", "ledger"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional fairyfly_therm_run target returned by therm_start_simulation.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional THERM run identifier when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Fairyfly THERM run record."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
