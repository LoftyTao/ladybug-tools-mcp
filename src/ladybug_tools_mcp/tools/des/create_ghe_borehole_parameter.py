"""Create Dragonfly DES BoreholeParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_ghe_borehole_parameter as service


def register(mcp: FastMCP) -> None:
    """Register the DES GHE borehole parameter tool."""

    @mcp.tool(
        name="create_ghe_borehole_parameter",
        description=(
            "Create a Dragonfly DES BoreholeParameter for GHE field sizing, "
            "including depth, spacing, buried depth, and borehole diameter. Use the "
            "returned target in GHE thermal loop authoring. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geothermal", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_borehole_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved BoreholeParameter target.")],
        min_depth: Annotated[float | None, Field(description="Optional minimum borehole depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_depth: Annotated[float | None, Field(description="Optional maximum borehole depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        min_spacing: Annotated[float | None, Field(description="Optional minimum borehole spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_spacing: Annotated[float | None, Field(description="Optional maximum borehole spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        buried_depth: Annotated[float | None, Field(description="Optional borehole buried depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        diameter: Annotated[float | None, Field(description="Optional borehole diameter in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES BoreholeParameter."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            min_depth=min_depth,
            max_depth=max_depth,
            min_spacing=min_spacing,
            max_spacing=max_spacing,
            buried_depth=buried_depth,
            diameter=diameter,
        )
