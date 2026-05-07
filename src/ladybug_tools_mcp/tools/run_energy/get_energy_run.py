"""Get Energy simulation run MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import get_energy_run as service


def register(mcp: FastMCP) -> None:
    """Register the get_energy_run tool."""

    @mcp.tool(
        name="get_energy_run",
        description="Get one Garden energy_run record by target or run_id without returning large result files.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "run",
            "ledger",
            "get",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_energy_run(
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
        """Get one Energy simulation run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
