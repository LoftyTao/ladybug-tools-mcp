"""Edit Honeybee Aperture MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_aperture as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_edit_aperture tool.'

    @mcp.tool(
        name="edit_aperture",
        description='Edit a Honeybee Aperture/window typed target for display name, user data, supported Face3D geometry, operable flag, Honeybee Energy window construction or VentilationOpening, and Honeybee Radiance modifier/dynamic states. Surface-adjacent interior Apertures do not support single-side geometry or operability edits. Requires garden_root and an aperture target, not an identifier string. Returns target, summary_view.updated_fields, persistence_receipt, and report for re-search, validation, or downstream Energy/Radiance translation.',
        tags={
            "aperture",
            "edit",
            "energy",
            "geometry",
            "honeybee",
            "modifier",
            "operable-window",
            "radiance",
            "surface",
            "ventilation-opening",
            "window",
        },
        timeout=20,
    )
    def edit_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee aperture typed target from honeybee_search_model_objects; not an aperture identifier string.'
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
        is_operable: Annotated[
            bool | None, Field(description="Optional updated is_operable flag for supported Apertures; Surface-adjacent interior Apertures cannot be edited one side at a time.")
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy window construction dictionary or Garden Properties Library construction target to attach or replace."
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
        radiance_modifier_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional Honeybee Radiance modifier target accepted as a bounded legacy input; prefer modifier for new calls."),
        ] = None,
        radiance_modifier: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional Honeybee Radiance modifier input accepted as a bounded legacy input; prefer modifier for new calls."),
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
        """Edit a Honeybee Aperture."""
        if modifier is None and radiance_modifier_target is not None:
            modifier = radiance_modifier_target
        if modifier is None and radiance_modifier is not None:
            modifier = radiance_modifier
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_operable=is_operable,
            construction=construction,
            vent_opening=vent_opening,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )
