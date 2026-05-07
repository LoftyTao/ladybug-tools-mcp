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
        identifier: Annotated[
            str | None,
            Field(description="Optional state label accepted for Agent compatibility."),
        ] = None,
        state_identifier: Annotated[
            str | int | None,
            Field(description="Optional state label accepted for Agent compatibility."),
        ] = None,
        shades: Annotated[
            list[dict[str, Any] | None] | None,
            Field(description="Optional list of StateGeometry dictionaries."),
        ] = None,
        states: Annotated[
            list[dict[str, Any] | None] | None,
            Field(description="Agent compatibility alias for shades; use it for StateGeometry dictionaries, not RadianceShadeState dictionaries."),
        ] = None,
        modifiers: Annotated[
            list[dict[str, Any] | None] | dict[str, Any] | str | None,
            Field(description="Agent compatibility alias. If a list of StateGeometry dictionaries is provided, it is treated as shades; otherwise it is treated as modifier."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root required when modifier is a Garden target."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Ignored compatibility hint; this tool returns a compact state dictionary."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceShadeState."""
        _ = return_object_dict
        if shades is None and states is not None:
            shades = states
        if modifiers is not None:
            if isinstance(modifiers, list) and shades is None:
                shades = modifiers
            elif modifier is None:
                modifier = modifiers
        if shades is not None:
            shades = [shade for shade in shades if shade is not None]
        result = service(modifier=modifier, shades=shades, garden_root=garden_root)
        result.setdefault("state_dict", result.get("object_dict"))
        return result
