"""Create Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_model as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_model tool.'

    @mcp.tool(
        name="create_model",
        description='Create an empty Honeybee Model in a Garden and optionally set it as the base Honeybee model with set_base. A Honeybee Model is the upstream container for Rooms, Faces, Apertures, Doors, and Shades; this does not create an EnergyPlus IDF, OpenStudio OSM, epJSON file, or Radiance scene. Returns compact target/model_target fields for downstream calls; object_dict is a compact target when saved and a full model body only when save_back=false and include_body=true. Normal authoring workflows should create the model first, then call honeybee_create_room for rooms. Use add_objects only when you already have complete Honeybee object dictionaries. Requires garden_root and identifier; do not pass arguments null or {}.',
        tags={
            "author",
            "honeybee",
            "model",
        },
        timeout=20,
    )
    def create_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
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
            bool,
            Field(
                description="Whether to persist the Honeybee Model to the Garden and return Garden targets/receipt fields."
            ),
        ] = True,
        set_base: Annotated[
            bool,
            Field(
                description="Whether to set as Garden base Honeybee model. Use set_base; not set_as_base."
            ),
        ] = True,
        include_body: Annotated[
            bool,
            Field(
                description="Whether to return the full Honeybee Model body when save_back is false; saved models return compact targets."
            ),
        ] = False,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description='Optional complete Honeybee object dictionaries to add while creating the model. Supports only full Room, Face, Aperture, Door, and Shade dictionaries; do not pass typed targets, program/load/construction dicts, or natural-language specs here. For normal modeling, omit add_objects and call honeybee_create_room next.'
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
