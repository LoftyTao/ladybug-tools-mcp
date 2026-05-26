"""Edit Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_room as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_edit_room tool.'

    @mcp.tool(
        name="edit_room",
        description='Edit a Honeybee Room display name, story, zone, multiplier, floor-area flag, Honeybee Energy ProgramType/ConstructionSet/HVAC-template/ventilation/setpoint properties, and Honeybee Radiance ModifierSet in a Garden model. Use target from honeybee_search_model_objects matches[i].target or honeybee_create_room.target; an exact same-model room identifier string is accepted only with the intended model_target. This is not Ironbug ThermalZone or DetailedHVAC component placement. Returns target, summary_view.updated_fields, persistence_receipt, and report for later search, validation, EnergyPlus translation, or Radiance workflows.',
        tags={
            "construction-set",
            "edit",
            "energy",
            "honeybee",
            "hvac-template",
            "modifier-set",
            "program-type",
            "radiance",
            "room",
            "setpoint",
            "ventilation",
        },
        timeout=20,
    )
    def edit_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any] | str,
            Field(
                description=(
                    "Required Honeybee room typed target dict from "
                    'honeybee_search_model_objects matches[i].target or '
                    'honeybee_create_room.target. Also accepts an exact '
                    "same-model room identifier string when model_target "
                    "selects the intended Honeybee Model."
                )
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
        multiplier: Annotated[
            int | None,
            Field(description="Optional updated room multiplier. Must be >= 1."),
        ] = None,
        zone: Annotated[
            str | None, Field(description="Optional updated Honeybee Room zone name; this is room metadata, not an Ironbug ThermalZone object.")
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
                description='Optional Honeybee Energy ProgramType dict, Garden target, or exact standards library identifier from energy_search_energy_library_objects matches[i].identifier, for example Generic Office Program. The parameter name is program_type, not energy_properties_program_type.'
            ),
        ] = None,
        construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Energy ConstructionSet dict, Garden target, or exact standards library identifier to attach or replace. Prefer energy_create_construction_set.target for custom sets.'
            ),
        ] = None,
        hvac: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee Energy HVAC dict or Garden Properties Library hvac target from energy_create_ideal_air_system or energy_search_hvac_templates. Do not hand-write fake HVAC dicts.'
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
                description='Optional zone ventilation fan collection update for Room.properties.energy.fans. Accepts a Garden Properties Library zone_ventilation_fan target, a list of fan dicts/targets for replace_all, or {operation: replace_all|add|clear, fans:[...]} from energy_create_zone_ventilation_fan. This is fan-assisted/mechanical zone ventilation, not operable-window natural ventilation.'
            ),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee Energy Setpoint dict or Garden Properties Library load target from energy_create_setpoint.target. The parameter name is setpoint, not energy_properties_setpoint. Do not pass a bare number; create a Setpoint with energy_create_setpoint(heating_setpoint=..., cooling_setpoint=..., garden_root=..., return_object_dict=false) and pass its target. Agents may pass a lightweight Setpoint dict with schedule identifiers instead of expanded schedule JSON.'
            ),
        ] = None,
        modifier_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Radiance ModifierSet dictionary or Garden Properties Library modifier_set target to attach or replace."
            ),
        ] = None,
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
