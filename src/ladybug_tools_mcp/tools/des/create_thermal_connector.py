"""Create Dragonfly DES ThermalConnector MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DES ThermalConnector authoring tool."""

    @mcp.tool(
        name="DF_des_thermal_connector",
        description=(
            "Create a Dragonfly DES ThermalConnector from Grasshopper-style 2D "
            "polyline points for a district thermal network. Use the returned target "
            "as a connector input for fifth-generation or GHE thermal loops. Returns "
            "target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geometry", "pipe", "target"},
        timeout=20,
    )
    def create_thermal_connector(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the saved Dragonfly DES ThermalConnector target."),
        ],
        polyline_points: Annotated[
            list[list[float]],
            Field(description="Ordered 2D points as [[x, y], ...]; two points create a line segment and three or more create a polyline."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display name stored on SDK objects that support display_name."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES ThermalConnector."""
        from garden.dragonfly_des.authoring import create_thermal_connector as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            polyline_points=polyline_points,
            display_name=display_name,
        )
