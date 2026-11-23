"""Poll Dragonfly DES Modelica simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register DF_des_poll_modelica_simulation."""

    @mcp.tool(
        name="DF_des_poll_modelica_simulation",
        description=(
            'Read the compact Garden ledger for a DES Modelica project write or Docker simulation '
            'to inspect runtime_status, poll_next, and output paths.'
        ),
        tags={"dragonfly", "district-energy", "poll", "runtime", "run", "target"},
        timeout=20,
    )
    def poll_modelica_simulation(
        garden_root: Annotated[str, Field(description='Garden root containing garden.json.')],
        run_target: Annotated[dict[str, Any] | None, Field(description=(
            'DES Modelica run target returned by DF_des_write_modelica_project or '
            'DF_des_start_modelica_simulation.'
        )) ] = None,
        run_id: Annotated[str | None, Field(description='Optional Modelica run id when run_target is not available.') ] = None,
    ) -> dict[str, Any]:
        """Poll a Modelica run."""
        from garden.dragonfly_des.runs import poll_modelica_simulation as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
