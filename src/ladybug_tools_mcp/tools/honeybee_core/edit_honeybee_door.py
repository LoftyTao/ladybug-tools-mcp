"""Edit Honeybee Door MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_door as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_edit_door tool.'

    @mcp.tool(
        name="edit_door",
        description='Edit a Honeybee Door typed target for display name, user data, supported Face3D geometry, glass flag, Honeybee Energy door construction or VentilationOpening, and Honeybee Radiance modifier/dynamic states. Surface-adjacent interior Door geometry updates are paired automatically on the adjacent Door, but single-side is_glass changes are rejected when paired state would diverge. Returns target, summary_view.updated_fields, persistence_receipt, and report for re-search, validation, or downstream Energy/Radiance translation.',
        tags={
            "door",
            "edit",
            "energy",
            "geometry",
            "glass-door",
            "hosted",
            "honeybee",
            "interior-door",
            "radiance",
            "surface",
            "ventilation-opening",
        },
        timeout=20,
    )
    def edit_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee door typed target from honeybee_search_model_objects; not a door identifier string. For Surface-adjacent interior doors, pass either side of the pair and geometry edits update the paired adjacent Door automatically.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
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
        is_glass: Annotated[
            bool | None, Field(description="Optional updated is_glass flag; Surface-adjacent interior door pairs cannot be changed to divergent glass states.")
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy door construction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        vent_opening: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy VentilationOpening dictionary to attach or replace."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from radiance_search_library_objects.'
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from radiance_search_library_objects.'
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance dynamic group identifier."),
        ] = None,
        states: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee Radiance state update. Accepts a state list for replace_all, or a dict with operation=replace_all|add|clear and states=[...]."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Door."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_glass=is_glass,
            construction=construction,
            vent_opening=vent_opening,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )
