"""Create Dragonfly Electric Grid Substation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_substation as service


def register(mcp: FastMCP) -> None:
    """Register the Grid Substation authoring tool."""

    @mcp.tool(
        name="substation",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS Substation from "
            "Grasshopper-style footprint points. Use the returned target in "
            "df_grid_electrical_network or df_grid_road_network. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "author", "target"},
        timeout=20,
    )
    def create_substation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid Substation target.")],
        footprint_points: Annotated[list[list[float]], Field(description="Closed or open 2D footprint points as [[x, y], ...].")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid Substation."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            display_name=display_name,
        )

