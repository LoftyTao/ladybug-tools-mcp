"""Start Dragonfly DES Modelica simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register DF_des_start_modelica_simulation."""

    @mcp.tool(
        name="DF_des_start_modelica_simulation",
        description=(
            'Start a Modelica Docker run from a DES modelica_project_target, returning '
            'run_target, runtime_status, poll_next, summary_view, and report (reports blocked '
            'when Docker, OpenModelica, or GMT is missing).'
        ),
        tags={"dragonfly", "district-energy", "simulate", "runtime", "run", "poll", "target"},
        timeout=30,
    )
    def start_modelica_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the Modelica run ledger is written inside this Garden.")],
        modelica_project_target: Annotated[dict[str, Any], Field(description='DES Modelica project artifact target returned by DF_des_write_modelica_project.')],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Start a Modelica simulation."""
        from garden.dragonfly_des.runs import start_modelica_simulation as service

        return service(
            garden_root=garden_root,
            modelica_project_target=modelica_project_target,
            run_id=run_id,
        )
