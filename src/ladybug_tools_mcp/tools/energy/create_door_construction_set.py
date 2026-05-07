"""Create DoorConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_door_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_door_construction_set tool."""

    @mcp.tool(
        name="create_door_construction_set",
        description="Create a Honeybee Energy DoorConstructionSet intermediate object for a full ConstructionSet. Accepts opaque and glass door construction overrides and returns slot values in summary_view.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "door",
            "subset",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_door_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Exterior opaque door OpaqueConstruction dict or identifier."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Interior opaque door OpaqueConstruction dict or identifier."
            ),
        ] = None,
        exterior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Exterior glass door WindowConstruction dict or identifier."
            ),
        ] = None,
        interior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Interior glass door WindowConstruction dict or identifier."
            ),
        ] = None,
        overhead_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Overhead opaque door OpaqueConstruction dict or identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming Garden Properties Library construction targets."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy DoorConstructionSet object."""
        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            exterior_glass_construction=exterior_glass_construction,
            interior_glass_construction=interior_glass_construction,
            overhead_construction=overhead_construction,
            garden_root=garden_root,
        )
