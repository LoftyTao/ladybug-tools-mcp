"""Edit Dragonfly Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_building as service


def register(mcp: FastMCP) -> None:
    """Register the edit_dragonfly_building tool."""

    @mcp.tool(
        name="edit_dragonfly_building",
        description="Edit a model-embedded Dragonfly Building using public Dragonfly SDK properties/methods. Supports display_name and sort_stories only; this is not a generic Building patch tool.",
        tags={"dragonfly-core", "garden-mode", "building", "edit", "write", "safe"},
        timeout=20,
    )
    def edit_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Identifier of the existing Dragonfly Building."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Building display name."),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Whether to run Dragonfly Building.sort_stories after edits."),
        ] = False,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Building."""
        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            model_target=model_target,
            display_name=display_name,
            sort_stories=sort_stories,
        )
