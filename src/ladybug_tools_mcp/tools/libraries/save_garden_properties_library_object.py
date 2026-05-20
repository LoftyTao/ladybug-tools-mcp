"""Save Garden Properties Library object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    save_garden_properties_library_object as service,
)


def register(mcp: FastMCP) -> None:
    """Register the save_garden_properties_library_object tool."""

    @mcp.tool(
        name="save_garden_properties_library_object",
        description="Save an existing full object_dict: save one Honeybee Energy or Honeybee Radiance SDK object dict into the Garden Properties Library as a reusable file-backed resource. Prefer direct Garden-saving create tools when they expose garden_root and return_object_dict=false, because those return target/summary/receipt without moving the full SDK object through Agent context. Use this tool for schedules, program types, loads, HVAC systems, materials, constructions, construction sets, modifiers, modifier sets, and luminaires when the object_dict already exists.",
        tags={
            "garden",
            "properties",
            "library",
            "save",
            "energy",
            "radiance",
            "persistent",
        },
        timeout=20,
    )
    def save_garden_properties_library_object(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        domain: Annotated[
            str,
            Field(description="Object domain: honeybee_energy or honeybee_radiance."),
        ],
        object_family: Annotated[
            str,
            Field(
                description="Object family: schedule, schedule_type_limit, program_type, load, hvac, material, construction, construction_set, modifier, modifier_set, or luminaire."
            ),
        ],
        object_dict: Annotated[
            dict[str, Any],
            Field(
                description="Existing full object_dict to save. Prefer direct Garden-saving create tools with garden_root and return_object_dict=false when available."
            ),
        ],
        identifier: Annotated[
            str | None, Field(description="Optional identifier override.")
        ] = None,
        overwrite: Annotated[
            bool, Field(description="Whether to overwrite an existing object.")
        ] = True,
    ) -> dict[str, Any]:
        """Save one object dict into the Garden Properties Library."""
        return service(
            garden_root=garden_root,
            domain=domain,
            object_family=object_family,
            object_dict=object_dict,
            identifier=identifier,
            overwrite=overwrite,
        )
