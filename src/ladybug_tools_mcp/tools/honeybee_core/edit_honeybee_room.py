"""Edit Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_room as service


def register(mcp: FastMCP) -> None:
    """Register the edit_honeybee_room tool."""

    @mcp.tool(
        name="edit_honeybee_room",
        description="Edit a Honeybee Room display name, story, zone, multiplier, floor-area flag, and room-level Energy or Radiance properties in a Garden model. Requires garden_root and edit_honeybee_room.target from search_honeybee_model_objects matches[i].target or create_honeybee_room.target. The parameter name is exactly target, not room_target; do not pass a room identifier string, do not pass the full search response, and do not pass matches[i] itself. Do not pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "room",
            "room-edit",
            "edit-room",
            "room-properties",
            "energy-properties",
            "construction-set",
            "program-type",
            "zone-ventilation",
            "mechanical-ventilation",
            "exhaust-fan",
            "write",
            "safe",
        },
        timeout=20,
    )
    def edit_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee room typed target dict for edit_honeybee_room.target. Use search_honeybee_model_objects matches[i].target or create_honeybee_room.target; the parameter name is exactly target, not room_target. Not a room identifier string; do not pass the full search response and do not pass matches[i] itself."
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
        multiplier: Annotated[
            int | None,
            Field(description="Optional updated room multiplier. Must be >= 1."),
        ] = None,
        zone: Annotated[
            str | None, Field(description="Optional updated Honeybee zone name.")
        ] = None,
        story: Annotated[
            str | None, Field(description="Optional updated story name.")
        ] = None,
        exclude_floor_area: Annotated[
            bool | None, Field(description="Optional updated exclude_floor_area flag.")
        ] = None,
        program_type: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Honeybee Energy ProgramType dict, Garden target, or exact standards library identifier from search_energy_library_objects matches[i].identifier, for example Generic Office Program."
            ),
        ] = None,
        construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Honeybee Energy ConstructionSet dict, Garden target, or exact standards library identifier to attach or replace. Prefer create_construction_set.target for custom sets."
            ),
        ] = None,
        hvac: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy HVAC dict or Garden Properties Library hvac target from create_ideal_air_system or search_hvac_templates with garden_root and return_object_dict=false. Do not hand-write fake HVAC dicts."
            ),
        ] = None,
        ventilation: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy Ventilation dict or Garden Properties Library load target."
            ),
        ] = None,
        zone_ventilation_fans: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="Optional zone ventilation fan collection update for Room.properties.energy.fans. Accepts a Garden Properties Library zone_ventilation_fan target, a list of fan dicts/targets for replace_all, or {operation: replace_all|add|clear, fans:[...]} from create_zone_ventilation_fan. This is fan-assisted/mechanical zone ventilation, not operable-window natural ventilation."
            ),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy Setpoint dict or Garden Properties Library load target. Agents may pass a lightweight Setpoint dict with schedule identifiers instead of expanded schedule JSON."
            ),
        ] = None,
        modifier_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Radiance ModifierSet dictionary to attach or replace."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Optional Agent hint accepted for compatibility. Ignored; edit_honeybee_room returns a compact edit receipt and summary."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Edit a Honeybee Room."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            multiplier=multiplier,
            zone=zone,
            story=story,
            exclude_floor_area=exclude_floor_area,
            program_type=program_type,
            construction_set=construction_set,
            hvac=hvac,
            ventilation=ventilation,
            zone_ventilation_fans=zone_ventilation_fans,
            setpoint=setpoint,
            modifier_set=modifier_set,
        )
