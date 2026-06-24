"""Start Dragonfly DES Modelica simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import start_modelica_simulation as service


def register(mcp: FastMCP) -> None:
    """Register the Modelica simulation candidate start tool."""

    @mcp.tool(
        name="start_modelica_simulation",
        description=(
            "Candidate boundary for starting a Modelica Docker run from a DES "
            "modelica_project_target. It records a Garden run ledger and returns "
            "run_target, runtime_status, poll_next, summary_view, and report. "
            "Missing Docker, OpenModelica, or GMT is reported as blocked, and "
            "numeric Modelica result reading is not exposed."
        ),
        tags={"dragonfly", "district-energy", "simulate", "runtime", "run", "poll", "target"},
        timeout=30,
    )
    def start_modelica_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the Modelica run ledger is written inside this Garden.")],
        modelica_project_target: Annotated[dict[str, Any], Field(description="DES Modelica project artifact target returned by the candidate project writer.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Start a candidate Modelica simulation."""
        return service(
            garden_root=garden_root,
            modelica_project_target=modelica_project_target,
            run_id=run_id,
        )
