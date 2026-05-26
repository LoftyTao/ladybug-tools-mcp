"""List Fairyfly THERM runs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import list_fairyfly_therm_runs as service


def register(mcp: FastMCP) -> None:
    'Register the therm_list_runs tool.'

    @mcp.tool(
        name="list_runs",
        description=(
            "List Fairyfly THERM run records stored in a Garden. Returns compact "
            "ledger entries, runtime_status values in summary_view, and report "
            "for two-dimensional heat-transfer runs. Use therm_poll_simulation on a "
            "specific run before result reads."
        ),
        tags={"fairyfly", "therm", "runtime", "search", "ledger"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_fairyfly_therm_runs(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status or readiness_status filter for Garden THERM run ledger records, such as completed, failed, or blocked."),
        ] = None,
    ) -> dict[str, Any]:
        """List Fairyfly THERM runs."""
        return service(garden_root=garden_root, status=status)
