"""Get Fairyfly THERM run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import get_fairyfly_therm_run as service


def register(mcp: FastMCP) -> None:
    """Register the get_fairyfly_therm_run tool."""

    @mcp.tool(
        name="get_fairyfly_therm_run",
        description=(
            "Get one Garden Fairyfly THERM run record by fairyfly_therm_run "
            "target or run_id. Use this after starting a THERM run to inspect "
            "completed, failed, or blocked THERM runs without returning large result data."
        ),
        tags={
            "fairyfly",
            "therm",
            "simulation",
            "2d-heat-transfer",
            "run",
            "ledger",
            "get",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional fairyfly_therm_run target returned by start_fairyfly_therm_run."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Fairyfly THERM run record."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
