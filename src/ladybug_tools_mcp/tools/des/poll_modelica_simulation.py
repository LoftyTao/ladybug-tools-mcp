"""Poll Dragonfly DES Modelica simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import poll_modelica_simulation as service


def register(mcp: FastMCP) -> None:
    """Register the Modelica candidate poll tool."""

    @mcp.tool(
        name="poll_modelica_simulation",
        description=(
            "Read the compact Garden ledger for a candidate DES Modelica project "
            "write or Docker simulation. Use it to inspect runtime_status, "
            "poll_next, and output paths while keeping numeric Modelica result "
            "values outside the public MCP surface."
        ),
        tags={"dragonfly", "district-energy", "poll", "runtime", "run", "target"},
        timeout=20,
    )
    def poll_modelica_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the candidate Modelica ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="DES Modelica candidate run target returned by the project writer or simulation starter.") ] = None,
        run_id: Annotated[str | None, Field(description="Modelica candidate run id to poll when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll a candidate Modelica run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
