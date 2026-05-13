"""Read Energy EUI MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import read_energy_eui as service


def register(mcp: FastMCP) -> None:
    """Register the read_energy_eui tool."""

    @mcp.tool(
        name="read_energy_eui",
        description=(
            "Read the completed EUI / energy use intensity output JSON "
            "summary for one Garden energy_run target. Use after get_energy_run or "
            "list_energy_run_outputs when the user asks to read completed "
            "EUI results."
        ),
        tags={
            "run-energy",
            "energy",
            "eui",
            "output",
            "result",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_eui(
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
        """Read Energy EUI summary."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
