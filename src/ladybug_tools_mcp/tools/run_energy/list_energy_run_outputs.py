"""List Energy simulation run outputs MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import list_energy_run_outputs as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_list_run_outputs tool.'

    @mcp.tool(
        name="list_run_outputs",
        description=(
            "List indexed output files for one Garden energy_run, including EUI "
            "JSON, ERR, SQL, HTML reports, and ZSZ when present. The same list "
            "is returned as matches, outputs, and files for easy result scanning. "
            "Use matches[i].name/path/exists to choose energyplus_read_eui, "
            "energyplus_read_errors, energyplus_read_result_data, or chart export."
        ),
        tags={
            "energy",
            "result",
            "outputs",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_run_outputs(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by energyplus_start_simulation; pass run_target unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation run outputs."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
