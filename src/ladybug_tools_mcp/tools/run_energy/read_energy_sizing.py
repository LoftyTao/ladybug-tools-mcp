"""Read EnergyPlus sizing MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the EP_read_sizing tool."""

    @mcp.tool(
        name="EP_read_sizing",
        description="Read compact zone peak loads and HVAC component sizing from a completed Garden Energy run. Filter by zone, component, or sizing category; it never returns raw SQL tables.",
        tags={"energy", "energyplus", "result", "sizing", "zone", "hvac"},
        timeout=30,
    )
    def read_energy_sizing(
        garden_root: Annotated[str, Field(description="Garden root path containing the completed Energy run.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Completed Energy run target.")] = None,
        run_id: Annotated[str | None, Field(description="Completed Energy run identifier.")] = None,
        zone: Annotated[str | None, Field(description="Optional zone-name substring filter.")] = None,
        component: Annotated[str | None, Field(description="Optional component-name substring filter.")] = None,
        sizing_category: Annotated[str | None, Field(description="Optional result category: zone, component, heating, or cooling.")] = None,
        max_results: Annotated[int, Field(description="Maximum compact sizing records to return.")] = 50,
    ) -> dict[str, Any]:
        """Read compact sizing results."""
        from garden.run_energy.sizing import read_energy_sizing as service
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id, zone=zone, component=component, sizing_category=sizing_category, max_results=max_results)
