"""Search Ironbug model objects MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import search_ironbug_model_objects as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_search_model_objects tool.'

    @mcp.tool(
        name="search_model_objects",
        description=(
            "Search compact objects inside a Garden-managed Ironbug .ibjson model. "
            "Use object_type=model, hvac_system, component, air_loop, plant_loop, vrf, "
            "energy_management_system, electric_load_center, or all. Returns matches "
            "with typed ironbug_model_object targets and compact summaries only; "
            "there is no include_body parameter. The result list field is matches, "
            "not ironbug_model_objects. This is not a Garden-wide model discovery "
            'tool; always pass ironbug_model_target from detailed_hvac_create_model.'
        ),
        tags={"ironbug", "detailed-hvac", "model", "search"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_ironbug_model_objects(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug target argument named ironbug_model_target; "
                    'pass the target returned by detailed_hvac_create_model, not ironbug_model. '
                    "This is required even when object_type='model'."
                )
            ),
        ],
        object_type: Annotated[
            str,
            Field(
                description=(
                    "Object type to return: all, model, hvac_system, air_loop, "
                    "component, plant_loop, vrf, energy_management_system, "
                    "or electric_load_center."
                )
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(description="Optional exact compact object identifier filter."),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Optional substring query over compact object identifiers."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of matches to return."),
        ] = None,
    ) -> dict[str, Any]:
        """Search Ironbug model objects and return typed targets."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            object_type=object_type,
            identifier=identifier,
            query=query,
            limit=limit,
        )
