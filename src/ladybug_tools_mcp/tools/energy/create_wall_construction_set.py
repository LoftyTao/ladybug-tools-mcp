"""Create WallConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_wall_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_wall_construction_set tool."""

    @mcp.tool(
        name="create_wall_construction_set",
        description="Create a Honeybee Energy WallConstructionSet intermediate object for a full ConstructionSet. Accepts exterior, interior, and ground OpaqueConstruction overrides and returns slot property values in summary_view.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "wall",
            "subset",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_wall_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Exterior wall OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Interior wall OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Ground wall OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming Garden Properties Library construction targets."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy WallConstructionSet object."""
        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            ground_construction=ground_construction,
            garden_root=garden_root,
        )
