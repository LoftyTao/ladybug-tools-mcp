"""Edit Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the edit_dragonfly_model tool."""

    @mcp.tool(
        name="edit_dragonfly_model",
        description=(
            "Edit Dragonfly Model metadata using public Dragonfly SDK properties. "
            "Supports only display_name, units, tolerance, and angle_tolerance; "
            "this is not a generic DFJSON patch tool. Do not use it to add Room2D, "
            "Story, or Building objects: create Story objects from Room2D draft "
            "targets, then create Buildings from Story targets."
        ),
        tags={"dragonfly-core", "garden-mode", "model", "edit", "write", "safe"},
        timeout=20,
    )
    def edit_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Accepts the typed target or "
                    "a Garden-relative DFJSON path. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional model target alias for natural calls. model_target "
                    "remains the canonical field."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Dragonfly Model display name."),
        ] = None,
        units: Annotated[
            str | None,
            Field(description="Optional Dragonfly Model units value accepted by the SDK, such as Meters."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly Model tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly Model angle tolerance in degrees."),
        ] = None,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Unsupported. Present only to return a clear error when a "
                    "natural agent tries to use edit_dragonfly_model as a generic "
                    "object insertion tool."
                )
            ),
        ] = None,
        model_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural identifier hint. Used only when model_target "
                    "and target are omitted."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural identifier hint. This does not rename the "
                    "Dragonfly model; use display_name for report-facing names."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Model."""
        if add_objects is not None:
            raise ValueError(
                "edit_dragonfly_model does not add Dragonfly objects. Create "
                "Room2D draft objects, pass them to create_dragonfly_story as "
                "room2d_targets, then pass Story targets to create_dragonfly_building."
            )
        if model_target is None:
            model_target = target
        if model_identifier is None and identifier is not None:
            model_identifier = identifier
        if model_target is None and model_identifier is not None:
            model_target = {
                "target_type": "model",
                "domain": "dragonfly",
                "model_identifier": model_identifier,
            }
        return service(
            garden_root=garden_root,
            model_target=model_target,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
