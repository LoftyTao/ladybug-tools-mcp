"""Read Energy ERR MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import read_energy_errors as service


def register(mcp: FastMCP) -> None:
    """Register the read_energy_errors tool."""

    @mcp.tool(
        name="read_energy_errors",
        description="Read a bounded EnergyPlus ERR text output for one Garden energy_run target and summarize warning/severe/fatal counts.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "err",
            "errors",
            "warnings",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_errors(
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
        max_chars: Annotated[
            int, Field(description="Maximum ERR text characters to return.")
        ] = 12000,
    ) -> dict[str, Any]:
        """Read Energy ERR output."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            max_chars=max_chars,
        )
