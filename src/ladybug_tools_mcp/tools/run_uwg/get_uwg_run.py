"""Get UWG run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import get_uwg_run as service


def register(mcp: FastMCP) -> None:
    """Register the get_uwg_run tool."""

    @mcp.tool(
        name="get_uwg_run",
        description="Read one Garden UWG run ledger record by uwg_run target or run_id.",
        tags={"run-uwg", "uwg", "alternative-weather", "read", "safe"},
        timeout=20,
    )
    def get_uwg_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_run target returned by start_uwg_run or run_uwg."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional UWG run id when run_target is not passed."),
        ] = None,
    ) -> dict[str, Any]:
        """Read a UWG run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
