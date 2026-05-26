"""Create DoorConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_door_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_door_construction_set tool.'

    @mcp.tool(
        name='create_door_construction_set',
        description="Create a Honeybee Energy DoorConstructionSet intermediate object for ConstructionSet door slots: exterior/interior opaque doors, exterior/interior glass doors, and overhead doors. Pass OpaqueConstruction or WindowConstruction object_dict values, Garden targets, or standards identifiers as appropriate. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into energy_create_construction_set.door_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "door",
            "window",
            "author",
        },
        timeout=20,
    )
    def create_door_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior opaque doors."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior opaque doors."
            ),
        ] = None,
        exterior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for exterior glass doors."
            ),
        ] = None,
        interior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for interior glass doors."
            ),
        ] = None,
        overhead_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for overhead opaque doors in roof/ceiling or floor parent faces."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
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
