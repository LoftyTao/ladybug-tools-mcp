"""Create Honeybee Radiance StateGeometry MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import create_radiance_state_geometry as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_state_geometry tool."""

    @mcp.tool(
        name="create_radiance_state_geometry",
        description="Create a Honeybee Radiance StateGeometry dictionary for use inside dynamic shade/subface states. Provide either geometry as a Ladybug Face3D dict or vertices as [[x,y,z], ...]. Optional modifier may be a modifier dict, Garden Properties Library modifier target, or standards-library identifier.",
        tags={
            "honeybee-radiance",
            "radiance",
            "dynamic",
            "state-geometry",
            "face3d",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_state_geometry(
        identifier: Annotated[
            str | None,
            Field(description="Radiance StateGeometry identifier. Defaults to state_geometry when omitted by an Agent."),
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
            Field(description="Optional Garden root required when modifier is a Garden target."),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(description="Ignored compatibility hint; this tool always returns a StateGeometry dictionary."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance StateGeometry."""
        _ = return_object_dict
        identifier = identifier or "state_geometry"
        return service(
            identifier=identifier,
            geometry=geometry,
            vertices=vertices,
            modifier=modifier,
            garden_root=garden_root,
        )
