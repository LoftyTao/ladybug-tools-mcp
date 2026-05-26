"""Create WallConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_wall_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_wall_construction_set tool.'

    @mcp.tool(
        name='create_wall_construction_set',
        description="Create a Honeybee Energy WallConstructionSet intermediate object for ConstructionSet wall slots: exterior walls, interior walls, and ground-contact walls. Pass OpaqueConstruction object_dict values, Garden targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into energy_create_construction_set.wall_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "wall",
            "author",
        },
        timeout=20,
    )
    def create_wall_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior walls."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior walls."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for ground-contact walls."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
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
