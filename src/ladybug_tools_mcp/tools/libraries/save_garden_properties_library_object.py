"""Save Garden Properties Library object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    save_garden_properties_library_object as service,
)


def register(mcp: FastMCP) -> None:
    'Register the library_save_garden_properties_object tool.'

    @mcp.tool(
        name="save_garden_properties_object",
        description="Save an existing full object_dict: save one Honeybee Energy or Honeybee Radiance SDK object dict into the Garden Properties Library as a reusable file-backed resource. Prefer direct Garden-saving create tools when they expose garden_root and return_object_dict=false, because those return target/summary/receipt without moving the full SDK object through Agent context. Use this tool for schedules, program types, loads, HVAC systems, materials, constructions, construction sets, modifiers, modifier sets, and luminaires when the object_dict already exists.",
        tags={
            "author",
            "energy",
            "library",
            "properties",
            "radiance",
        },
        timeout=20,
    )
    def save_garden_properties_library_object(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")
        ],
        domain: Annotated[
            str,
            Field(description="Object domain: honeybee_energy or honeybee_radiance."),
        ],
        object_family: Annotated[
            str,
            Field(
                description=(
                    "Object family in the selected Garden Properties Library "
                    "domain. Common values include schedule, schedule_type_limit, "
                    "program_type, load, hvac, material, construction, "
                    "construction_set, modifier, modifier_set, and luminaire."
                )
            ),
        ],
        object_dict: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Existing complete Honeybee Energy or Honeybee Radiance SDK "
                    "object_dict to validate and save. Prefer direct "
                    "Garden-saving create tools with garden_root and "
                    "return_object_dict=false when available."
                )
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional saved object identifier override. Omit to derive the "
                    "identifier from object_dict when the SDK object provides one."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Whether to overwrite an existing Garden Properties Library "
                    "object with the same domain, object_family, and identifier."
                )
            ),
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
