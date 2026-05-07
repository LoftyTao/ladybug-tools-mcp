"""Create Honeybee Radiance subface state MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import create_radiance_subface_state as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_subface_state tool."""

    @mcp.tool(
        name="create_radiance_subface_state",
        description="Create a Honeybee RadianceSubFaceState dictionary for dynamic Apertures or Doors. Optional modifier may be a modifier dict, Garden Properties Library modifier target, or standards-library identifier. Optional shades is a list of StateGeometry dictionaries from create_radiance_state_geometry.",
        tags={
            "honeybee-radiance",
            "radiance",
            "dynamic",
            "subface-state",
            "aperture",
            "door",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_subface_state(
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        shades: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional list of StateGeometry dictionaries."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root required when modifier is a Garden target."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceSubFaceState."""
        return service(modifier=modifier, shades=shades, garden_root=garden_root)
