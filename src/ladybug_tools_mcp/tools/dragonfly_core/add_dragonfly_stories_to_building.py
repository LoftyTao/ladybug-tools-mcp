"""Add Dragonfly Stories to Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import add_dragonfly_stories_to_building as service


def register(mcp: FastMCP) -> None:
    """Register the add_dragonfly_stories_to_building tool."""

    @mcp.tool(
        name="add_dragonfly_stories_to_building",
        description=(
            "Add Dragonfly Story draft targets to an existing Building using Dragonfly "
            "Building.add_stories, then save the DFJSON model. The existing Building is "
            "selected by building_identifier; do not pass a building target as target. "
            "After adding, the service uses Dragonfly SDK Building.separate_top_bottom_floors "
            "so repeated Story multipliers keep explicit ground, typical, and top Stories."
        ),
        tags={"dragonfly-core", "garden-mode", "building", "story", "edit", "write", "safe"},
        timeout=20,
    )
    def add_dragonfly_stories_to_building(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Required list of Dragonfly Story targets to add."),
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
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
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
