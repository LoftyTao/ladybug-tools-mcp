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
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional Dragonfly Model display name.")
        ] = None,
        units: Annotated[
            str | None,
            Field(description="Optional Dragonfly Model units value accepted by the SDK, such as Meters."),
        ] = None,
        tolerance: Annotated[
            float | None, Field(description="Optional Dragonfly Model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly Model angle tolerance in degrees."),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Model."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
