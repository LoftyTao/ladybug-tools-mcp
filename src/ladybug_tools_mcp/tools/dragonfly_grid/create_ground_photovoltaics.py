"""Create Dragonfly Electric Grid GroundMountPV MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_ground_photovoltaics as service


def register(mcp: FastMCP) -> None:
    """Register the Grid GroundMountPV authoring tool."""

    @mcp.tool(
        name="ground_photovoltaics",
        description=(
            "Create a Dragonfly Energy REopt GroundMountPV object from footprint "
            "points. This authors PV geometry for Grid/REopt export handoff; it "
            "does not run EnergyPlus, OpenDSS, or REopt. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "electric-grid", "reopt", "photovoltaic", "pv", "author", "target"},
        timeout=20,
    )
    def create_ground_photovoltaics(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the GroundMountPV target.")],
        footprint_points: Annotated[list[list[float]], Field(description="2D ground-mounted PV footprint points as [[x, y], ...].")],
        building_identifier: Annotated[str | None, Field(description="Optional Dragonfly Building identifier associated with this PV system.")] = None,
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Energy GroundMountPV object."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            building_identifier=building_identifier,
            display_name=display_name,
        )
