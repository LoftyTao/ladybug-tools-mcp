"""Create ApertureConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_aperture_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_aperture_construction_set tool."""

    @mcp.tool(
        name="create_aperture_construction_set",
        description="Create a Honeybee Energy ApertureConstructionSet intermediate object for a full ConstructionSet. Accepts WindowConstruction overrides and returns slot property values in summary_view.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "aperture",
            "window",
            "subset",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_aperture_construction_set(
        window_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Exterior window WindowConstruction dict or library identifier."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Interior aperture WindowConstruction dict or library identifier."
            ),
        ] = None,
        skylight_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Skylight WindowConstruction dict or library identifier."
            ),
        ] = None,
        operable_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Operable WindowConstruction dict or library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming Garden Properties Library construction targets."
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
