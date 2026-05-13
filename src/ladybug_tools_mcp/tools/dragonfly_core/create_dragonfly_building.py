"""Create Dragonfly Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_building as service


def register(mcp: FastMCP) -> None:
    """Register the create_dragonfly_building tool."""

    @mcp.tool(
        name="create_dragonfly_building",
        description=(
            "Create a Dragonfly Building in a Garden Dragonfly model from Dragonfly Story "
            "targets and save the DFJSON model. The service uses Dragonfly SDK "
            "Building.separate_top_bottom_floors before saving so repeated Story "
            "multipliers become explicit ground, typical, and top Stories where needed. "
            "Pass identifier or a natural display_name."
        ),
        tags={"dragonfly-core", "garden-mode", "building", "create", "write", "safe"},
        timeout=20,
    )
    def create_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Required list of Dragonfly Story targets. Use story_target "
                    "values returned by create_dragonfly_story or target values "
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
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Accepts the typed target or a "
                    "Garden-relative DFJSON path. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Whether to sort stories by floor height."),
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
        height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural project height hint. Story geometry controls "
                    "the actual Dragonfly Building height."
                )
            ),
        ] = None,
        room2d_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Natural-language recovery alias for story_targets when the "
                    "list actually contains Story targets. Do not pass raw Room2D "
                    "targets here; create a Story first."
                )
            ),
        ] = None,
        story_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional natural Story identifier list. Used only for draft "
                    "Stories already saved in the Garden."
                )
            ),
        ] = None,
        stories_count: Annotated[
            int | None,
            Field(description="Optional natural count hint; Story targets control actual stories."),
        ] = None,
        story_height: Annotated[
            float | None,
            Field(description="Optional natural height hint; Story objects control actual height."),
        ] = None,
        building_type: Annotated[
            str | None,
            Field(description="Optional natural building type hint for Agent notes."),
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
            height=height,
            room2d_targets=room2d_targets,
            story_identifiers=story_identifiers,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        if stories_count is not None or story_height is not None or building_type is not None:
            result["summary_view"]["natural_hints"] = {
                "stories_count": stories_count,
                "story_height": story_height,
                "building_type": building_type,
            }
        return result
