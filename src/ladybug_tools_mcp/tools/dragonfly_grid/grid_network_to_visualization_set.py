"""Dragonfly Electric Grid network VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.display import grid_network_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the Grid network VisualizationSet handoff tool."""

    @mcp.tool(
        name="network_to_visualization_set",
        description=(
            "Create a compact Ladybug Display VisualizationSet target for a "
            "Dragonfly Electric Grid ElectricalNetwork. Use the returned "
            "visualization_set_target with shared visualization exporters."
        ),
        tags={"dragonfly", "electric-grid", "visualization", "visualization-set", "target"},
        timeout=20,
    )
    def grid_network_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        network_target: Annotated[dict[str, Any], Field(description="ElectricalNetwork target returned by df_grid_electrical_network.")],
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/display name.")] = None,
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict; keep false for compact target handoff.")] = False,
    ) -> dict[str, Any]:
        """Create a VisualizationSet target for an Electric Grid network."""
        return service(
            garden_root=garden_root,
            network_target=network_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

