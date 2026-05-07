"""List Energy simulation runs MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import list_energy_runs as service


def register(mcp: FastMCP) -> None:
    """Register the list_energy_runs tool."""

    @mcp.tool(
        name="list_energy_runs",
        description="List annual energy-use simulation runs recorded in a Garden run ledger.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "runs",
            "ledger",
            "list",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_runs(
        garden_root: Annotated[
            str, Field(description="Garden root containing garden.json.")
        ],
        status: Annotated[
            str | None,
            Field(
                description="Optional run status filter, such as completed or failed."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation runs."""
        return service(garden_root=garden_root, status=status)
