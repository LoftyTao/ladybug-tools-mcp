"""Create Dragonfly DES GroundHeatExchanger MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_ground_heat_exchanger as service


def register(mcp: FastMCP) -> None:
    """Register the DES GroundHeatExchanger authoring tool."""

    @mcp.tool(
        name="create_ground_heat_exchanger",
        description=(
            "Create a Dragonfly DES GroundHeatExchanger from a 2D field footprint "
            "and optional SDK-required 3D borehole positions. Use the returned target "
            "as a ground heat exchanger input for a GHE thermal loop. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geometry", "geothermal", "ground-heat-exchanger", "target"},
        timeout=20,
    )
    def create_ground_heat_exchanger(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GroundHeatExchanger target.")],
        footprint_points: Annotated[list[list[float]], Field(description="Ordered 2D footprint points as [[x, y], ...] for the GHE field polygon.")],
        borehole_positions: Annotated[list[list[float]] | None, Field(description="Optional borehole Point3D coordinates as [[x, y, z], ...], matching the current Dragonfly Energy SDK requirement.")] = None,
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GroundHeatExchanger."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            borehole_positions=borehole_positions,
            display_name=display_name,
        )
