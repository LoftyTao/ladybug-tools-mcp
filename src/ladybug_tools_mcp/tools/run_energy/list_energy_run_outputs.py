"""List Energy simulation run outputs MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import list_energy_run_outputs as service


def register(mcp: FastMCP) -> None:
    """Register the list_energy_run_outputs tool."""

    @mcp.tool(
        name="list_energy_run_outputs",
        description="List indexed output files for one Garden energy_run, including EUI JSON, ERR, SQL, HTML reports, and ZSZ when present.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "outputs",
            "sql",
            "err",
            "eui",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_run_outputs(
        garden_root: Annotated[
            str, Field(description="Garden root containing garden.json.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional energy_run target returned by run_energy."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation run outputs."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
