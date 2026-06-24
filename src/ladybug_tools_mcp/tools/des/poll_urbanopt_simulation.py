"""Poll Dragonfly DES URBANopt simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import poll_urbanopt_simulation as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt poll tool."""

    @mcp.tool(
        name="poll_urbanopt_simulation",
        description=(
            "Read the compact Garden ledger for an URBANopt DES run. Use it "
            "after the start tool to check runtime_status, poll_next, and the "
            "output inventory before load assignment or system-parameter work. "
            "The response does not open SQL, ERR, HTML, CSV, or log bodies."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "poll", "runtime", "run", "target"},
        timeout=20,
    )
    def poll_urbanopt_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="URBANopt DES run target returned by the start tool.") ] = None,
        run_id: Annotated[str | None, Field(description="URBANopt run id to poll when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll an URBANopt run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
