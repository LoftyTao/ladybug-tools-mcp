"""Create Dragonfly Electric Grid ElectricalConnector MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_electrical_connector as service


def register(mcp: FastMCP) -> None:
    """Register the Grid ElectricalConnector authoring tool."""

    @mcp.tool(
        name="electrical_connector",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS ElectricalConnector from "
            "2D polyline points and a power-line identifier returned by "
            "df_grid_search_opendss. Use the target in df_grid_electrical_network."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "connector", "author", "target"},
        timeout=20,
    )
    def create_electrical_connector(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid ElectricalConnector target.")],
        polyline_points: Annotated[list[list[float]], Field(description="Ordered 2D connector points as [[x, y], ...].")],
        power_line_identifier: Annotated[str, Field(description="OpenDSS power-line identifier from df_grid_search_opendss.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid ElectricalConnector."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            polyline_points=polyline_points,
            power_line_identifier=power_line_identifier,
            display_name=display_name,
        )

