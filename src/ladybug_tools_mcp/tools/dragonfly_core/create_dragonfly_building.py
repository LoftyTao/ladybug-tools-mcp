"""Create Dragonfly Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_building as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_create_building tool.'

    @mcp.tool(
        name="create_building",
        description=(
            "Create a Dragonfly Building in a Garden Dragonfly model from Dragonfly Story "
            "targets and save the DFJSON model. The service uses Dragonfly SDK "
            "Building.separate_top_bottom_floors before saving so repeated Story "
            "multipliers become explicit ground, typical, and top Stories where needed. "
            'Use this after dragonfly_create_room2d and dragonfly_create_story when '
            "assembling a building story room2d model. Returns target, summary_view, "
            "persistence_receipt, and report for a Dragonfly Building, not a Honeybee "
            "Model or EnergyPlus Zone."
        ),
        tags={"dragonfly", "building", "story", "room2d", "author", "model", "assembly"},
        timeout=20,
    )
    def create_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Required list of Dragonfly Story targets. Use story_target "
                    'values returned by dragonfly_create_story or target values '
                    "from a Story search."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly Building identifier. If omitted, display_name "
                    "is converted to a stable identifier."
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
        sort_stories: Annotated[
            bool,
            Field(description="Whether to sort Dragonfly Stories by floor height before saving the Building."),
        ] = True,
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional user-facing Building name. If identifier is omitted, "
                    "spaces are converted to underscores for the identifier."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional low-cost output control. Set false to omit the full "
                    "Building object_dict while keeping targets, summary, receipt, "
                    "and report."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Building."""
        result = service(
            garden_root=garden_root,
            identifier=identifier,
            story_targets=story_targets,
            model_target=model_target,
            sort_stories=sort_stories,
            display_name=display_name,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        return result
