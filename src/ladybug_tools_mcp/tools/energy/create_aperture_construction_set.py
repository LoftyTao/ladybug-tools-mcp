"""Create ApertureConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_aperture_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_aperture_construction_set tool.'

    @mcp.tool(
        name='create_aperture_construction_set',
        description="Create a Honeybee Energy ApertureConstructionSet intermediate object for ConstructionSet aperture slots: fixed exterior windows, interior apertures, skylights, and operable windows. Pass WindowConstruction object_dict values, Garden Properties Library targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into energy_create_construction_set.aperture_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "aperture",
            "window",
            "skylight",
            "operable-window",
            "author",
        },
        timeout=20,
    )
    def create_aperture_construction_set(
        window_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for fixed exterior windows in wall apertures."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for interior apertures with Surface boundary conditions."
            ),
        ] = None,
        skylight_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for skylights in roof/ceiling or floor parent faces."
            ),
        ] = None,
        operable_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for operable exterior windows."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ApertureConstructionSet object."""
        return service(
            window_construction=window_construction,
            interior_construction=interior_construction,
            skylight_construction=skylight_construction,
            operable_construction=operable_construction,
            garden_root=garden_root,
        )
