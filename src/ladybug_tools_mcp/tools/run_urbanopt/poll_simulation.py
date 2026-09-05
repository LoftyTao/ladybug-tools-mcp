"""Poll URBANopt Energy simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the URBANopt Energy poll tool."""

    @mcp.tool(
        name="DF_urbanopt_poll_simulation",
        description=(
            "Read the compact Garden ledger for an URBANopt Energy simulation. "
            "Use this after urbanopt_start_simulation to inspect run_target, "
            "runtime_status, poll_next, summary_view, and report without "
            "claiming building energy results that are not present."
        ),
        tags={"dragonfly", "urbanopt", "energy", "run", "runtime", "poll", "target"},
        timeout=10,
    )
    def poll_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Optional urbanopt_run target returned by urbanopt_start_simulation.") ] = None,
        run_id: Annotated[str | None, Field(description="Optional URBANopt run id when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll an URBANopt Energy simulation."""
        from garden.run_urbanopt.run import poll_simulation as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
