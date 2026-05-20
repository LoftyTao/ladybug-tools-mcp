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
        description="Search Honeybee Energy standards library identifiers for schedules, schedule type limits, program types, materials, constructions, and construction sets. Use returned identifiers in energy foundation tools. This searches built-in standards, not Garden files. This does not search room thermostat Setpoints; for heating_setpoint/cooling_setpoint values call create_setpoint. Required call shape: {\"query\":\"generic office lighting\",\"object_family\":\"schedule\",\"limit\":3}.",
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
                description="Optional family filter: schedule, schedule_type_limit, program_type, opaque_material, window_material, opaque_construction, window_construction, shade_construction, construction_set, or all. Not setpoint; use create_setpoint with heating_setpoint and cooling_setpoint for thermostat setpoints."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Energy standards library identifiers."""
        return service(
            query=query,
            object_family=object_family,
            limit=limit,
        )
