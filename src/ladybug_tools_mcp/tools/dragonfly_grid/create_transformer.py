"""Create Dragonfly Electric Grid Transformer MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_transformer as service


def register(mcp: FastMCP) -> None:
    """Register the Grid Transformer authoring tool."""

    @mcp.tool(
        name="transformer",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS Transformer from footprint "
            "points and an OpenDSS transformer properties identifier returned by "
            "df_grid_search_opendss. Returns a compact Grid target for network assembly."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "transformer", "author", "target"},
        timeout=20,
    )
    def create_transformer(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid Transformer target.")],
        footprint_points: Annotated[list[list[float]], Field(description="2D transformer footprint points as [[x, y], ...].")],
        transformer_properties_identifier: Annotated[str, Field(description="OpenDSS transformer properties identifier from df_grid_search_opendss.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid Transformer."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            transformer_properties_identifier=transformer_properties_identifier,
            display_name=display_name,
        )

