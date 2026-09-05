"""List Dragonfly DES URBANopt run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the URBANopt output listing tool."""

    @mcp.tool(
        name="DF_des_list_urbanopt_run_outputs",
        description=(
            "List the saved output files for one Garden URBANopt DES run as "
            "compact path records. Use after polling has found completed or "
            "failed status when an Agent needs to locate SQL, ERR, HTML, CSV, "
            "or log files without reading their contents. Accepts run_target or "
            "run_id and returns matches, summary_view, and report."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "outputs", "run", "artifact", "target"},
        timeout=20,
    )
    def list_urbanopt_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; output records are discovered under this Garden's run folder.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="URBANopt DES run target whose outputs should be listed.") ] = None,
        run_id: Annotated[str | None, Field(description="URBANopt run id to list when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """List URBANopt run outputs."""
        from garden.dragonfly_des.runs import list_urbanopt_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
