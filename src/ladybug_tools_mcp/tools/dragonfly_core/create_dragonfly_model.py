"""Create Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_create_model tool.'

    @mcp.tool(
        name="create_model",
        description=(
            "Create an empty Dragonfly model in a Garden and optionally set it as the "
            "base Dragonfly model with set_base; not set_as_base. Returns target and "
            "model_target for downstream Dragonfly calls. Add Room2D, Story, and "
            "Building objects with the dedicated Dragonfly authoring tools."
        ),
        tags={"dragonfly", "model", "author", "garden", "dfjson"},
        timeout=20,
    )
    def create_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description=(
                    "Required Dragonfly model identifier or natural project name. "
                    "Spaces and illegal SDK identifier characters are cleaned for "
                    "the stored DFJSON identifier."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Dragonfly model display name."),
        ] = None,
        units: Annotated[
            str,
            Field(description="Dragonfly model units string, for example Meters."),
        ] = "Meters",
        unit_system: Annotated[
            str | None,
            Field(
                description="Optional natural unit-system selection. Metric maps to Meters; Imperial maps to Feet."
            ),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional model tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Model angle tolerance."),
        ] = 1.0,
        save_back: Annotated[
            bool,
            Field(description="Whether to save the Dragonfly Model into the Garden and return a Dragonfly model target."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(
                description="Whether to set as Garden base Dragonfly model. Use set_base; not set_as_base."
            ),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return full model body if not saved."),
        ] = False,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional compact-return flag used across Garden create tools. "
                    "False keeps the default compact model target response; True "
                    "requests the full body only when save_back is false."
                )
            ),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional project latitude context saved as model user_data."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional project longitude context saved as model user_data."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Model."""
        if unit_system is not None:
            normalized_unit_system = unit_system.strip().lower()
            if normalized_unit_system in {"metric", "si"}:
                units = "Meters"
            elif normalized_unit_system in {"imperial", "ip"}:
                units = "Feet"
            else:
                units = unit_system
        if return_object_dict is not None:
            include_body = bool(return_object_dict)
        return service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
            latitude=latitude,
            longitude=longitude,
        )
