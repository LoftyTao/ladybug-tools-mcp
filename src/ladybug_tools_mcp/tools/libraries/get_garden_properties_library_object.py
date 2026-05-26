"""Get Garden Properties Library object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    get_garden_properties_library_object as service,
)


def register(mcp: FastMCP) -> None:
    'Register the library_get_garden_properties_object tool.'

    @mcp.tool(
        name="get_garden_properties_object",
        description=(
            "Read one saved Honeybee Energy or Honeybee Radiance reusable object "
            "from the Garden Properties Library by typed target or by domain, "
            "object_family, and identifier. Use this after "
            "library_search_garden_properties_objects or when a stored "
            "garden_properties_library_object target is already available. Returns "
            "object_dict, target, summary_view, and report. This is not a built-in "
            "standards-library reader and it does not transparently read "
            "legacy wrapper-style storage; run "
            "library_normalize_garden_properties_storage first when files need "
            "native SDK JSON normalization."
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
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Garden Properties Library object target with "
                    "target_type='garden_properties_library_object', usually from "
                    "library_search_garden_properties_objects['matches'][i]['target']."
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
        return service(
            garden_root=garden_root,
            target=target,
            domain=domain,
            object_family=object_family,
            identifier=identifier,
        )
