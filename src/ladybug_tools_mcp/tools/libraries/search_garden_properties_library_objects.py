"""Search Garden Properties Library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    search_garden_properties_library_objects as service,
)


def register(mcp: FastMCP) -> None:
    """Register the search_garden_properties_library_objects tool."""

    @mcp.tool(
        name="search_garden_properties_library_objects",
        description="Search saved Garden properties and reusable object targets in the Garden Properties Library, including Honeybee Energy schedules, program types, constructions, construction sets, HVAC, and Honeybee Radiance modifiers, modifier sets, or luminaires. Use this for Garden-saved targets, not built-in standards libraries. Returns targets for later get, edit, or assignment workflows. Use query, domain, and object_family to narrow results.",
        tags={
            "garden",
            "properties",
            "library",
            "search",
            "read-only",
            "energy",
            "radiance",
            "saved-garden-properties",
            "reusable-object-targets",
            "construction-set",
            "program-type",
            "schedule",
            "modifier",
            "luminaire",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_garden_properties_library_objects(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        query: Annotated[
            str, Field(description="Search text for identifier or object type.")
        ] = "",
        domain: Annotated[
            str | None,
            Field(
                description="Optional domain filter: honeybee_energy, honeybee_radiance, or all."
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description="Optional object family filter, such as schedule, program_type, modifier, or luminaire."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of matches to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Garden Properties Library object indexes."""
        return service(
            garden_root=garden_root,
            query=query,
            domain=domain,
            object_family=object_family,
            limit=limit,
        )
