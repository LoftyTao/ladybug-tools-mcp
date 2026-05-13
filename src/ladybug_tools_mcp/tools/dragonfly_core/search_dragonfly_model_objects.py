"""Search Dragonfly Model Objects MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.search import search_dragonfly_model_objects as service


def register(mcp: FastMCP) -> None:
    """Register the search_dragonfly_model_objects tool."""

    @mcp.tool(
        name="search_dragonfly_model_objects",
        description="Search Dragonfly Buildings, Stories, Room2Ds, and ContextShades in the Garden base Dragonfly model or an explicit Dragonfly model target. Also returns draft Room2D and Story objects saved in the Garden before they are assembled into a Building. Use object_type=building, object_type=story, object_type=room2d, object_type=context_shade, or object_type=all. For Dragonfly rooms, object_type is room2d; do not pass room. Returns compact matches with nested Dragonfly object targets for follow-up tools. Defaults to compact summaries without geometry; set include_geometry=true only when the Room2D floor geometry summary is needed.",
        tags={
            "dragonfly-core",
            "garden-mode",
            "model",
            "search",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_dragonfly_model_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly model target dict. Defaults to the Garden base Dragonfly model."
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
            Field(description="Optional token query over identifier and display name."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Optional parent Building identifier filter."),
        ] = None,
        parent_building: Annotated[
            str | None,
            Field(description="Optional natural alias for building_identifier."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional parent Story identifier filter for Room2Ds."),
        ] = None,
        parent_story: Annotated[
            str | None,
            Field(description="Optional natural alias for story_identifier."),
        ] = None,
        floor_identifier_pattern: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural floor/story identifier pattern. Used as "
                    "query when query is omitted."
                )
            ),
        ] = None,
        children_scope: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Dragonfly Building or Story object target used to return only child Stories or Room2Ds. A string is treated as a parent identifier."
            ),
        ] = None,
        include_geometry: Annotated[
            bool,
            Field(
                description="Whether to include compact Room2D Face3D floor geometry summaries. Defaults false to avoid large object payloads."
            ),
        ] = False,
        include_child_counts: Annotated[
            bool | None,
            Field(description="Optional natural hint accepted for compact searches; child counts are already summarized where available."),
        ] = None,
    ) -> dict[str, Any]:
        """Search Dragonfly objects and return compact typed targets."""
        if building_identifier is None:
            building_identifier = parent_building
        if story_identifier is None:
            story_identifier = parent_story
        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
            query=query,
            building_identifier=building_identifier,
            story_identifier=story_identifier,
            floor_identifier_pattern=floor_identifier_pattern,
            children_scope=children_scope,
            include_geometry=include_geometry,
        )
