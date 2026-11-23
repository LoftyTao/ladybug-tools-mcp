"""libraries MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register libraries tools."""

    @mcp.tool(
        name="GD_Library_Get_Garden_Properties_Object",
        description=(
            'Read one saved Honeybee Energy or Honeybee Radiance reusable object from the Garden '
            'Properties Library by typed target or by domain, object_family, and identifier. Use '
            'this after GD_Library_Search_Garden_Properties_Objects or when a stored '
            'garden_properties_library_object target is already available. Returns object_dict, '
            'target, summary_view, and report. Reads Garden-saved library files.'
        ),
        tags={
            "energy",
            "library",
            "properties",
            "radiance",
            "target",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_garden_properties_library_object(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root'].")
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Garden Properties Library object target with "
                    "target_type='garden_properties_library_object', usually from "
                    "GD_Library_Search_Garden_Properties_Objects['matches'][i]['target']."
                )
            ),
        ] = None,
        domain: Annotated[
            str | None,
            Field(
                description=(
                    "Optional domain when target is omitted: honeybee_energy or "
                    "honeybee_radiance."
                )
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    "Optional object family when target is omitted, such as "
                    "schedule, construction_set, modifier, or luminaire."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional object identifier when target is omitted; use it "
                    "together with domain and object_family."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read one Garden Properties Library object."""
        from garden.libraries.properties import (
            get_garden_properties_library_object as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            domain=domain,
            object_family=object_family,
            identifier=identifier,
        )

    @mcp.tool(
        name="GD_Library_Save_Garden_Properties_Object",
        description=(
            'Save an existing full object_dict: save one Honeybee Energy or Honeybee Radiance SDK '
            'object dict into the Garden Properties Library as a reusable file-backed resource. '
            'When creating new resources, direct create tools with garden_root and '
            'return_object_dict=false save directly and return compact targets. Use this tool for '
            'schedules, program types, loads, HVAC systems, materials, constructions, '
            'construction sets, modifiers, modifier sets, and luminaires when the object_dict '
            'already exists.'
        ),
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
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root'].")
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
        from garden.libraries.properties import (
            save_garden_properties_library_object as service,
        )

        return service(
            garden_root=garden_root,
            domain=domain,
            object_family=object_family,
            object_dict=object_dict,
            identifier=identifier,
            overwrite=overwrite,
        )

    @mcp.tool(
        name="GD_Library_Search_Garden_Properties_Objects",
        description=(
            'Search saved Garden Properties Library indexes for reusable Honeybee Energy and '
            'Honeybee Radiance object targets, including schedules, program types, loads, HVAC '
            'systems, materials, constructions, construction sets, modifiers, modifier sets, and '
            'luminaires. Returns matches with domain, object_family, identifier, object_type, '
            'path, target, plus summary_view and report; pass matches[*].target to '
            'GD_Library_Get_Garden_Properties_Object or downstream assignment workflows.'
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
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root'].")
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
        from garden.libraries.properties import (
            search_garden_properties_library_objects as service,
        )

        return service(
            garden_root=garden_root,
            query=query,
            domain=domain,
            object_family=object_family,
            limit=limit,
        )
