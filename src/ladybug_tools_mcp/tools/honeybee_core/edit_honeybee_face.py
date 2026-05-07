"""Edit Honeybee Face MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_face as service


def register(mcp: FastMCP) -> None:
    """Register the edit_honeybee_face tool."""

    @mcp.tool(
        name="edit_honeybee_face",
        description="Edit a Honeybee Face geometry, type, boundary condition, display name, user data, and face-level energy or radiance properties in a Garden model. Requires garden_root and target from search_honeybee_model_objects; do not pass arguments null or {}.",
        tags={"honeybee-core", "garden-mode", "face", "geometry", "write", "safe"},
        timeout=20,
    )
    def edit_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face typed target from search_honeybee_model_objects; not a face identifier string."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Optional replacement user_data dictionary."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Face3D dict, for example {'type':'Face3D','boundary':[[x,y,z],...]}; not Rhino geometry."
            ),
        ] = None,
        type: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional updated Honeybee Face type name or dict."),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional updated Honeybee boundary condition name or dict."
            ),
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy opaque construction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        vent_crack: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy AFNCrack dictionary to attach or replace."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from search_radiance_library_objects."
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from search_radiance_library_objects."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Face."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            type=type,
            boundary_condition=boundary_condition,
            construction=construction,
            vent_crack=vent_crack,
            modifier=modifier,
            modifier_blk=modifier_blk,
        )
