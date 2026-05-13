"""Remove Dragonfly Stories from Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import (
    remove_dragonfly_stories_from_building as service,
)


def register(mcp: FastMCP) -> None:
    """Register the remove_dragonfly_stories_from_building tool."""

    @mcp.tool(
        name="remove_dragonfly_stories_from_building",
        description=(
            "Remove Stories from a Dragonfly Building using Dragonfly "
            "Building.remove_stories_by_identifier. Select the Building with "
            "building_identifier and Story IDs with story_identifiers. This does not "
            "remove Buildings or Room2Ds because those are not exposed as stable "
            "Dragonfly SDK remove APIs. After removal, the service uses Dragonfly SDK "
            "Building.separate_top_bottom_floors so the remaining Stories keep explicit "
            "ground, typical, and top semantics."
        ),
        tags={"dragonfly-core", "garden-mode", "building", "story", "remove", "write", "safe"},
        timeout=20,
    )
    def remove_dragonfly_stories_from_building(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building."),
        ],
        story_identifiers: Annotated[
            list[str],
            Field(description="Required Story identifiers to remove from the Building."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Stories from a Building."""
        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            story_identifiers=story_identifiers,
            model_target=model_target,
        )
