"""List URBANopt Energy run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_urbanopt.run import list_run_outputs as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt Energy output listing tool."""

    @mcp.tool(
        name="list_run_outputs",
        description=(
            "List discovered output files for an URBANopt Energy simulation run. "
            "Use this after urbanopt_poll_simulation to find SQL, ERR, HTML, "
            "CSV, OSM, IDF, log, and other URBANopt/EnergyPlus artifacts before "
            "calling downstream diagnostics or DES load tools. Returns "
            "run_target, runtime_status, matches, summary_view, and report."
        ),
        tags={"dragonfly", "urbanopt", "energy", "energyplus", "outputs", "run", "artifact", "target"},
        timeout=10,
    )
    def list_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; output paths are returned relative to this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Optional urbanopt_run target returned by urbanopt_start_simulation.") ] = None,
        run_id: Annotated[str | None, Field(description="Optional URBANopt run id when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """List URBANopt Energy run outputs."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
