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
        description="Create an empty Honeybee model in a Garden and optionally set it as the base model. Returns target and model_target for downstream calls. Ordinary Agent workflows should create the model first, then call create_honeybee_room for rooms; do not use add_objects unless you already have complete Honeybee Room, Face, Aperture, Door, or Shade object dictionaries. Requires garden_root and identifier; do not pass arguments null or {}.",
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
                description="Optional natural unit-system alias such as Metric or Imperial. Metric maps to Meters; Imperial maps to Feet."
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(
                description="Optional Agent-friendly display-name hint; accepted but not persisted separately from the Honeybee model identifier."
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
            bool, Field(description="Whether to set as Garden base model.")
        ] = True,
        is_base_model: Annotated[
            bool | None,
            Field(
                description="Optional Agent alias for set_base. Accepted when a model asks to mark this as the base model."
            ),
        ] = None,
        set_as_base: Annotated[
            bool | None,
            Field(
                description="Optional Agent alias for set_base. Accepted for compatibility with natural language workflows."
            ),
        ] = None,
        include_body: Annotated[
            bool, Field(description="Whether to return full model body if not saved.")
        ] = False,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description="Optional Agent compactness hint accepted for compatibility. Ignored because saved model calls already return compact targets."
            ),
        ] = None,
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
        if is_base_model is not None:
            set_base = is_base_model
        if set_as_base is not None:
            set_base = set_as_base
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
