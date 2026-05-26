"""Create Honeybee Radiance StateGeometry MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import create_radiance_state_geometry as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_state_geometry tool.'

    @mcp.tool(
        name="create_state_geometry",
        description=(
            "Create a Honeybee Radiance StateGeometry dictionary for dynamic "
            "shade or subface states. Provide geometry as a Ladybug Face3D "
            "dict or vertices as [[x, y, z], ...]. Optional modifier may be a "
            "modifier dict, Garden Properties Library modifier target, or "
            "standards-library identifier. This returns a state-geometry "
            "object_dict for state tools; it does not save a Garden target or "
            "edit the model by itself."
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "state-geometry",
            "dynamic-state",
        },
        timeout=20,
    )
    def create_radiance_state_geometry(
        identifier: Annotated[
            str | None,
            Field(description="Honeybee Radiance StateGeometry identifier. Defaults to state_geometry when omitted by an Agent."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Geometry Face3D dictionary."),
        ] = None,
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="Optional vertices as [[x, y, z], ...]. Use instead of geometry."),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance StateGeometry."""
        identifier = identifier or "state_geometry"
        return service(
            identifier=identifier,
            geometry=geometry,
            vertices=vertices,
            modifier=modifier,
            garden_root=garden_root,
        )
