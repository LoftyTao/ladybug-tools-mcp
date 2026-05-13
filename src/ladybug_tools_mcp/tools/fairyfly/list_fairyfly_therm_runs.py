"""List Fairyfly THERM runs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import list_fairyfly_therm_runs as service


def register(mcp: FastMCP) -> None:
    """Register the list_fairyfly_therm_runs tool."""

    @mcp.tool(
        name="list_fairyfly_therm_runs",
        description=(
            "List Fairyfly THERM run records stored in a Garden. Returns compact "
            "ledger entries for completed, failed, or blocked two-dimensional "
            "heat-transfer runs."
        ),
        tags={
            "fairyfly",
            "therm",
            "simulation",
            "2d-heat-transfer",
            "run",
            "ledger",
            "search",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_fairyfly_therm_runs(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        status: Annotated[
            str | None,
            Field(description="Optional status filter, for example completed, failed, or blocked."),
        ] = None,
    ) -> dict[str, Any]:
        """List Fairyfly THERM runs."""
        return service(garden_root=garden_root, status=status)
