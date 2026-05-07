"""Search Honeybee Energy standards library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.libraries import search_energy_library_objects as service


def register(mcp: FastMCP) -> None:
    """Register the search_energy_library_objects tool."""

    @mcp.tool(
        name="search_energy_library_objects",
        description="Search Honeybee Energy standards library identifiers for schedules, schedule type limits, program types, materials, constructions, and construction sets. Use returned identifiers in energy foundation tools. This searches built-in standards, not the Garden, so garden_root is accepted only as an ignored Agent context hint.",
        tags={
            "honeybee-energy",
            "energy",
            "library",
            "standards",
            "search",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_energy_library_objects(
        query: Annotated[
            str,
            Field(
                description="Search text, such as 'generic office lighting' or 'fractional'."
            ),
        ],
        object_family: Annotated[
            str | None,
            Field(
                description="Optional family filter: schedule, schedule_type_limit, program_type, opaque_material, window_material, construction for all construction families, opaque_construction, window_construction, shade_construction, construction_set, or all."
            ),
        ] = None,
        object_type: Annotated[
            str | None,
            Field(
                description="Optional Agent-friendly object type filter with the same values as object_family. If both are provided, object_family wins."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
        garden_root: Annotated[
            str | None,
            Field(
                description="Ignored Agent context hint. Built-in Energy library search does not read Garden files; use search_garden_properties_library_objects for saved Garden objects."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search Honeybee Energy standards library identifiers."""
        _ = garden_root
        return service(
            query=query,
            object_family=object_family,
            object_type=object_type,
            limit=limit if limit is not None else limit,
        )
