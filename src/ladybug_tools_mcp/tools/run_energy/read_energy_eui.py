"""Read Energy EUI MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import read_energy_eui as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_read_eui tool.'

    @mcp.tool(
        name="read_eui",
        description='Read EUI / energy use intensity JSON for one Garden energy_run after runtime_status is finished. Use after energyplus_poll_simulation or energyplus_list_run_outputs confirms result artifacts exist; this reads the lightweight annual summary, not SQL time series. Returns eui, result_evidence, summary_view, and report; if EUI is missing, returns energy_blocker with recommended_next_tools instead of a DataCollection target.',
        tags={
            "energy",
            "result",
            "eui",
            "summary",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_eui(
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
        """Read Energy EUI summary."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
