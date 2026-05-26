"""Search Garden Properties Library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    search_garden_properties_library_objects as service,
)


def register(mcp: FastMCP) -> None:
    'Register the library_search_garden_properties_objects tool.'

    @mcp.tool(
        name="search_garden_properties_objects",
        description=(
            "Search saved Garden Properties Library indexes for reusable Honeybee "
            "Energy and Honeybee Radiance object targets, including schedules, "
            "program types, loads, HVAC systems, materials, constructions, "
            "construction sets, modifiers, modifier sets, and luminaires. Use this "
            "for Garden-saved reusable resources, not built-in standards-library "
            "search. Returns matches with domain, object_family, identifier, "
            "object_type, path, target, plus summary_view and report; pass "
            "matches[*].target to library_get_garden_properties_object or downstream "
            "assignment workflows."
        ),
        tags={
            "energy",
            "library",
            "properties",
            "radiance",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_garden_properties_library_objects(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")
        ],
        query: Annotated[
            str,
            Field(
                description=(
                    "Search text matched against saved object identifiers and SDK "
                    "object_type values. Use an empty string to list recent objects "
                    "within the selected domain/object_family."
                )
            ),
        ] = "",
        domain: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden Properties Library domain filter: "
                    "honeybee_energy, honeybee_radiance, or all."
                )
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    "Optional saved object family filter, such as schedule, "
                    "program_type, construction_set, modifier, or luminaire."
                )
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of Garden-saved matches to return.")
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
