"""Create Dragonfly Electric Grid ElectricalNetwork MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_electrical_network as service


def register(mcp: FastMCP) -> None:
    """Register the Grid ElectricalNetwork authoring tool."""

    @mcp.tool(
        name="electrical_network",
        description=(
            "Create a Dragonfly Electric Grid ElectricalNetwork from a Substation "
            "target plus Transformer and ElectricalConnector targets. Pass the "
            "returned target into Dragonfly-to-GeoJSON/export workflows when grid "
            "export support is available."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "network", "author", "target"},
        timeout=20,
    )
    def create_electrical_network(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the ElectricalNetwork target.")],
        substation_target: Annotated[dict[str, Any], Field(description="Target returned by df_grid_substation.")],
        transformer_targets: Annotated[list[dict[str, Any]], Field(description="Transformer targets returned by df_grid_transformer.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="ElectricalConnector targets returned by df_grid_electrical_connector.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid ElectricalNetwork."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            substation_target=substation_target,
            transformer_targets=transformer_targets,
            connector_targets=connector_targets,
            display_name=display_name,
        )

