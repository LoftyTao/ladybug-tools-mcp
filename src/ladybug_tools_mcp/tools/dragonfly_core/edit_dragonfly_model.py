"""Edit Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the DF_edit_model tool.'

    @mcp.tool(
        name="DF_edit_model",
        description=(
            "Edit Dragonfly Model metadata using public Dragonfly SDK properties. "
            "Supports only display_name, units, tolerance, and angle_tolerance; "
            "this is not a generic DFJSON patch tool. Do not use it to add Room2D, "
            "Story, or Building objects: create Story objects from Room2D draft "
            "targets, then create Buildings from Story targets. Returns the updated "
            "Dragonfly model target and summary."
        ),
        tags={"dragonfly", "model", "edit", "summary", "metadata", "dfjson"},
        timeout=20,
    )
    def edit_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional Dragonfly Model display name saved on the Garden model.")
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
        from garden.dragonfly_core.editing import edit_dragonfly_model as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
