"""Create Honeybee Radiance shade state MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import create_radiance_shade_state as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_shade_state tool."""

    @mcp.tool(
        name="create_radiance_shade_state",
        description="Create a Honeybee RadianceShadeState dictionary for dynamic Shades. Optional modifier may be a modifier dict, Garden Properties Library modifier target, or standards-library identifier. Optional shades is a list of StateGeometry dictionaries from create_radiance_state_geometry. Return value is an object_dict/state_dict, not a Garden target; pass shade_state['object_dict'] into setup_radiance_dynamic_group states=[...] in the same execute block.",
        tags={
            "honeybee-radiance",
            "radiance",
            "dynamic",
            "shade-state",
            "shade",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_shade_state(
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        shades: Annotated[
            list[dict[str, Any] | None] | None,
            Field(description="Optional list of StateGeometry dictionaries."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root required when modifier is a Garden target."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceShadeState."""
        if shades is not None:
            shades = [shade for shade in shades if shade is not None]
        result = service(modifier=modifier, shades=shades, garden_root=garden_root)
        result.setdefault("state_dict", result.get("object_dict"))
        return result
