"""Create Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_model as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_model tool."""

    @mcp.tool(
        name="create_honeybee_model",
        description="Create an empty Honeybee model in a Garden and optionally set it as the base Honeybee model with set_base; not set_as_base. Returns target and model_target for downstream calls; no return_object_dict parameter is available because this tool already returns compact targets unless include_body=true is requested, and no display_name parameter is available. Ordinary Agent workflows should create the model first, then call create_honeybee_room for rooms; do not use add_objects unless you already have complete Honeybee Room, Face, Aperture, Door, or Shade object dictionaries. Requires garden_root and identifier; do not pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "base-model",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required Honeybee model identifier used for the stable Garden HBJSON file name."
            ),
        ],
        units: Annotated[
            str, Field(description="Honeybee model units string, for example Meters.")
        ] = "Meters",
        unit_system: Annotated[
            str | None,
            Field(
                description="Optional unit system such as Metric or Imperial. Metric maps to Meters; Imperial maps to Feet."
            ),
        ] = None,
        tolerance: Annotated[
            float | None, Field(description="Optional model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float, Field(description="Model angle tolerance.")
        ] = 1.0,
        save_back: Annotated[
            bool, Field(description="Whether to save the model into Garden.")
        ] = True,
        set_base: Annotated[
            bool,
            Field(
                description="Whether to set as Garden base Honeybee model. Use set_base; not set_as_base."
            ),
        ] = True,
        include_body: Annotated[
            bool, Field(description="Whether to return full model body if not saved.")
        ] = False,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional complete Honeybee object dictionaries to add while creating the model. Supports only full Room, Face, Aperture, Door, and Shade dictionaries; do not pass typed targets, program/load/construction dicts, or natural-language specs here. For normal modeling, omit add_objects and call create_honeybee_room next."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Model."""
        if unit_system is not None:
            normalized_unit_system = unit_system.strip().lower()
            if normalized_unit_system in {"metric", "si"}:
                units = "Meters"
            elif normalized_unit_system in {"imperial", "ip"}:
                units = "Feet"
            else:
                units = unit_system
        return service(
            garden_root=garden_root,
            identifier=identifier,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
            add_objects=add_objects,
        )
