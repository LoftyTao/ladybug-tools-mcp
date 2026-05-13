"""List UWG run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import list_uwg_run_outputs as service


def register(mcp: FastMCP) -> None:
    """Register the list_uwg_run_outputs tool."""

    @mcp.tool(
        name="list_uwg_run_outputs",
        description="List compact output records for one UWG run.",
        tags={"run-uwg", "uwg", "alternative-weather", "outputs", "read", "safe"},
        timeout=20,
    )
    def list_uwg_run_outputs(
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
        """List UWG run outputs."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
