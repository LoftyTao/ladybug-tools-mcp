"""Add Dragonfly Stories to Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import add_dragonfly_stories_to_building as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_add_stories_to_building tool.'

    @mcp.tool(
        name="add_stories_to_building",
        description=(
            "Add Dragonfly Story draft targets to an existing Building using Dragonfly "
            "Building.add_stories, then save the DFJSON model. The existing Building is "
            "selected by building_identifier; do not pass a building target as target. "
            "After adding, the service uses Dragonfly SDK Building.separate_top_bottom_floors "
            "so repeated Story multipliers keep explicit ground, typical, and top Stories. "
            "Returns the updated Dragonfly Building/model target context, not EnergyPlus Zone data."
        ),
        tags={"dragonfly", "building", "story", "edit", "assembly"},
        timeout=20,
    )
    def add_dragonfly_stories_to_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Required list of Dragonfly Story targets returned by dragonfly_create_story or Dragonfly object search."),
        ] = None,
        story_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional natural recovery input for draft Story identifiers. "
                    "When used, the service resolves each identifier to the Garden "
                    "draft Story object for the active Dragonfly model."
                )
            ),
        ] = None,
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
        """Add Dragonfly Stories to a Building."""
        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            story_targets=story_targets,
            model_target=model_target,
            story_identifiers=story_identifiers,
        )
