"""Create Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the HB_create_model tool.'

    @mcp.tool(
        name="HB_create_model",
        description=(
            'Create an empty Honeybee Model in a Garden and optionally set it as the base '
            'Honeybee model with set_base. A Honeybee Model is the upstream container for Rooms, '
            'Faces, Apertures, Doors, and Shades. Returns compact target/model_target fields for '
            'downstream calls; object_dict is a compact target when saved and a full model body '
            'only when save_back=false and include_body=true. Typically followed by '
            'HB_create_room for rooms (use add_objects when supplying complete Honeybee object '
            'dictionaries). Requires garden_root and identifier.'
        ),
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
                description="Required Garden root path containing garden.json, usually GD_create['garden_root']."
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
                description='Whether to set as the Garden base Honeybee model.'
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
                description=(
                    'Optional complete Honeybee Room, Face, Aperture, Door, or Shade object '
                    'dictionaries to include at creation (for typical modeling, omit and call '
                    'HB_create_room next).'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Model."""
        from garden.honeybee_core.creation import create_honeybee_model as service

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
