"""Search Dragonfly Model Objects MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.search import search_dragonfly_model_objects as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_search_model_objects tool.'

    @mcp.tool(
        name="search_model_objects",
        description=(
            "Search Dragonfly Buildings, Stories, Room2Ds, and ContextShades in the "
            "Garden base Dragonfly model or an explicit Dragonfly model target. Also "
            "returns draft Room2D and Story objects saved in the Garden before they are "
            "assembled into a Building. Use object_type=building, story, room2d, "
            "context_shade, or all; for Dragonfly rooms, use room2d. Returns compact "
            "matches with nested Dragonfly object targets for follow-up tools. Set "
            "include_geometry=true only when a Room2D floor geometry summary is needed."
        ),
        tags={"dragonfly", "model", "search", "summary", "inventory"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_dragonfly_model_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        object_type: Annotated[
            str,
            Field(
                description="Object type to return: all, building, story, room2d, or context_shade. Use room2d for Dragonfly rooms; do not pass room."
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(
                description="Optional exact Dragonfly object identifier or display name filter."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Optional token query over Dragonfly object identifier and display name."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Optional parent Building identifier filter."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional parent Story identifier filter for Room2Ds."),
        ] = None,
        children_scope: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly Building or Story object target used to return only child Stories or Room2Ds."
            ),
        ] = None,
        include_geometry: Annotated[
            bool,
            Field(
                description="Whether to include compact Room2D Face3D floor geometry summaries. Defaults false to avoid large object payloads."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Search Dragonfly objects and return compact typed targets."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
            query=query,
            building_identifier=building_identifier,
            story_identifier=story_identifier,
            children_scope=children_scope,
            include_geometry=include_geometry,
        )
