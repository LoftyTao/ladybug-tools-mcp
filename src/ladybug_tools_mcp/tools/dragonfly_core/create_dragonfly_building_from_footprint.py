"""Create Dragonfly Building from footprint MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DF_building_from_footprint tool."""

    @mcp.tool(
        name="DF_building_from_footprint",
        description=(
            "Create a Dragonfly Building from explicit footprint point loops and "
            "floor-to-floor heights. This is the MCP-native form of Grasshopper "
            "DF Building from Footprint: pass Python point lists or Garden "
            "targets, not Rhino Breps or Grasshopper data trees."
        ),
        tags={"dragonfly", "building", "footprint", "geometry", "author"},
        timeout=60,
    )
    def create_dragonfly_building_from_footprint(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(description="Dragonfly Building identifier or natural name."),
        ],
        footprints: Annotated[
            list[list[list[float]]],
            Field(description="Footprint point loops as [[[x, y], ...], ...]."),
        ],
        floor_to_floor_heights: Annotated[
            list[float],
            Field(description="Floor-to-floor heights for each intended floor."),
        ],
        perimeter_offset: Annotated[
            float | None,
            Field(description="Optional perimeter/core offset passed to Dragonfly SDK."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Building display name."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geometry tolerance."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Building from footprint point loops."""
        from garden.dragonfly_core.creation import (
            create_dragonfly_building_from_footprint as service,
        )

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprints=footprints,
            floor_to_floor_heights=floor_to_floor_heights,
            perimeter_offset=perimeter_offset,
            model_target=model_target,
            display_name=display_name,
            tolerance=tolerance,
        )
