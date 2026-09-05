"""Create Dragonfly Electric Grid RoadNetwork MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the Grid RoadNetwork authoring tool."""

    @mcp.tool(
        name="DF_grid_road_network",
        description=(
            "Create a Dragonfly Electric Grid RNM RoadNetwork from a Substation "
            "target and road segment dictionaries. Road segments use "
            "{identifier, polyline_points}. Returns a compact target for RNM workflows."
        ),
        tags={"dragonfly", "electric-grid", "rnm", "road", "network", "author", "target"},
        timeout=20,
    )
    def create_road_network(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the RoadNetwork target.")],
        substation_target: Annotated[dict[str, Any], Field(description="Target returned by DF_grid_substation.")],
        road_segments: Annotated[list[dict[str, Any]], Field(description="Road segment dicts with identifier and polyline_points fields.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid RoadNetwork."""
        from garden.dragonfly_grid.authoring import create_road_network as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            substation_target=substation_target,
            road_segments=road_segments,
            display_name=display_name,
        )
