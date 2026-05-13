"""List UWG runs MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import list_uwg_runs as service


def register(mcp: FastMCP) -> None:
    """Register the list_uwg_runs tool."""

    @mcp.tool(
        name="list_uwg_runs",
        description="List Garden UWG Alternative Weather run ledger records.",
        tags={"run-uwg", "uwg", "alternative-weather", "read", "safe"},
        timeout=20,
    )
    def list_uwg_runs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        status: Annotated[
            str | None,
            Field(description="Optional status filter such as running, completed, or failed."),
        ] = None,
    ) -> dict:
        """List UWG runs."""
        return service(garden_root=garden_root, status=status)
