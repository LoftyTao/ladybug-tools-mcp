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
            str | None,
            Field(
                description=(
                    "Identifier of the existing Dragonfly Building. May be omitted "
                    "when target is a Dragonfly Building target."
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
        target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Building target alias."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for target."),
        ] = None,
        building_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for a Dragonfly Building target."),
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
        if target is None:
            target = host_target or building_target
        if building_identifier is None and target is not None:
            building_identifier = target.get("object_identifier") or target.get("identifier")
        if building_identifier is None:
            raise ValueError(
                "edit_dragonfly_building requires building_identifier or a Building target."
            )
        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            model_target=model_target,
            display_name=display_name,
            sort_stories=sort_stories,
        )
