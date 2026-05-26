"""Search Honeybee Energy standards library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.libraries import search_energy_library_objects as service


def register(mcp: FastMCP) -> None:
    'Register the energy_search_energy_library_objects tool.'

    @mcp.tool(
        name='search_energy_library_objects',
        description=(
            "Search Honeybee Energy standards library identifiers for "
            "schedules, program types, materials, constructions, and "
            "construction sets. Use returned identifiers in Energy authoring "
            "tools. This searches built-in standards and does not search "
            "Garden files, EnergyPlus result files, or Ironbug objects. For "
            "thermostat setpoints use energy_create_setpoint. Returns matches, "
            "identifiers, summary_view, and report."
        ),
        tags={
            "energy",
            "library",
            "search",
            "standards",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_energy_library_objects(
        query: Annotated[
            str,
            Field(
                description="Search text for Honeybee Energy standards identifiers, such as 'generic office lighting' or 'fractional'."
            ),
        ],
        object_family: Annotated[
            str | None,
            Field(
                description='Optional family filter: schedule, schedule_type_limit, program_type, opaque_material, window_material, opaque_construction, window_construction, shade_construction, construction_set, or all. Not setpoint; use energy_create_setpoint with heating_setpoint and cooling_setpoint for thermostat setpoints.'
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
