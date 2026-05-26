"""Edit Dragonfly Building MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_building as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_edit_building tool.'

    @mcp.tool(
        name="edit_building",
        description=(
            "Edit a model-embedded Dragonfly Building using public Dragonfly SDK "
            "properties/methods. Supports display_name and sort_stories only; this is "
            "not a generic Building patch tool. Returns target, summary_view, and "
            "report for the updated Dragonfly model context."
        ),
        tags={"dragonfly", "building", "edit", "model", "metadata"},
        timeout=20,
    )
    def edit_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
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
