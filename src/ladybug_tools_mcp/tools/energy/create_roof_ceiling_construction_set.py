"""Create RoofCeilingConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_roof_ceiling_construction_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_roof_ceiling_construction_set tool."""

    @mcp.tool(
        name="create_roof_ceiling_construction_set",
        description="Create a Honeybee Energy RoofCeilingConstructionSet intermediate object for a full ConstructionSet. Returns slot property values in summary_view.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "roof",
            "ceiling",
            "subset",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_roof_ceiling_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Exterior roof OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Interior ceiling OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Ground roof/floor OpaqueConstruction dict or library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming Garden Properties Library construction targets."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy RoofCeilingConstructionSet object."""
        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            ground_construction=ground_construction,
            garden_root=garden_root,
        )
