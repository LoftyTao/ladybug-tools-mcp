"""Remove Dragonfly Stories from Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import (
    remove_dragonfly_stories_from_building as service,
)


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_remove_stories_from_building tool.'

    @mcp.tool(
        name="remove_stories_from_building",
        description=(
            "Remove Stories from a Dragonfly Building using Dragonfly "
            "Building.remove_stories_by_identifier. Select the Building with "
            "building_identifier and Story IDs with story_identifiers. This does not "
            "remove Buildings or Room2Ds because those are not exposed as stable "
            "Dragonfly SDK remove APIs. After removal, the service uses Dragonfly SDK "
            "Building.separate_top_bottom_floors so the remaining Stories keep explicit "
            "ground, typical, and top semantics. Returns target, summary_view, and report "
            "for the updated Dragonfly Building/model context."
        ),
        tags={"dragonfly", "building", "story", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_stories_from_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
        ],
        story_identifiers: Annotated[
            list[str],
            Field(description="Required Dragonfly Story identifiers to remove from the Building."),
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
    ) -> dict[str, Any]:
        """Remove Dragonfly Stories from a Building."""
        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            story_identifiers=story_identifiers,
            model_target=model_target,
        )
