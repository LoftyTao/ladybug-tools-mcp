"""Edit Honeybee Shade MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_shade as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_edit_shade tool.'

    @mcp.tool(
        name="edit_shade",
        description='Edit a Honeybee Shade typed target for display name, user data, supported Face3D geometry, detached flag on orphaned shades, Honeybee Energy ShadeConstruction/transmittance schedule/PVProperties, and Honeybee Radiance modifier/dynamic states. Hosted shades keep their parent relationship and cannot be made detached by setting is_detached=true. Returns target, summary_view.updated_fields, persistence_receipt, and report for re-search, validation, or downstream Energy/Radiance translation.',
        tags={
            "detached-shade",
            "edit",
            "energy",
            "geometry",
            "hosted",
            "honeybee",
            "pv",
            "radiance",
            "shade",
            "shading",
            "transmittance-schedule",
        },
        timeout=20,
    )
    def edit_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee shade typed target from honeybee_search_model_objects; not a shade identifier string.'
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
        is_detached: Annotated[
            bool | None,
            Field(description="Optional updated detached flag for orphaned shades only; hosted shades cannot be detached in place."),
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy ShadeConstruction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        transmittance_schedule: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy schedule dictionary or Garden Properties Library schedule target for shade transmittance."
            ),
        ] = None,
        pv_properties: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee Energy PVProperties dictionary or Garden Properties Library pv_properties target from energy_create_pv_properties to attach or replace.'
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
        """Edit a Honeybee Shade."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_detached=is_detached,
            construction=construction,
            transmittance_schedule=transmittance_schedule,
            pv_properties=pv_properties,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )
