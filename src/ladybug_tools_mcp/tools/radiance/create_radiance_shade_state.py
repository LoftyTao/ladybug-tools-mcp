"""Create Honeybee Radiance shade state MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import create_radiance_shade_state as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_shade_state tool.'

    @mcp.tool(
        name="create_shade_state",
        description=(
            "Create a Honeybee RadianceShadeState dictionary for dynamic "
            "Shades. Optional modifier may be a modifier dict, Garden "
            "Properties Library modifier target, or standards-library "
            "identifier. Optional shades is a list of StateGeometry "
            "dictionaries from radiance_create_state_geometry. Return value is "
            "an object_dict/state_dict, not a Garden target; pass it into "
            "radiance_setup_dynamic_group states=[...] before running recipes."
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "shade-state",
            "dynamic-state",
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
            Field(description="Optional list of Radiance StateGeometry dictionaries for dynamic shade geometry."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceShadeState."""
        if shades is not None:
            shades = [shade for shade in shades if shade is not None]
        result = service(modifier=modifier, shades=shades, garden_root=garden_root)
        result.setdefault("state_dict", result.get("object_dict"))
        return result
