"""Add Ironbug HVAC component MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import add_ironbug_hvac_component as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_add_hvac_component_fallback tool.'

    @mcp.tool(
        name="add_hvac_component_fallback",
        description=(
            "Create a reviewed fallback Ironbug component only when "
            'detailed_hvac_list_hvac_component_types returns the requested type and no '
            "source-backed create_ironbug_* tool exists. Prefer exact source-backed "
            'tools such as detailed_hvac_fan_on_off, '
            'detailed_hvac_coil_cooling_water, or '
            'detailed_hvac_pump_constant_speed. Returns target, summary_view, '
            "persistence_receipt, and report for .ibjson assembly."
        ),
        tags={"ironbug", "detailed-hvac", "component", "author"},
        timeout=20,
    )
    def add_ironbug_hvac_component(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target named ironbug_model_target; "
                    "pass detailed_hvac_create_model['target'], not ironbug_model."
                )
            ),
        ],
        component_type: Annotated[
            str,
            Field(
                description=(
                    'Component type id from detailed_hvac_list_hvac_component_types, '
                    "for example pump_constant_speed, boiler_hot_water, "
                    "coil_heating_water, or heat_exchanger_fluid_to_fluid; use "
                    "component_type, not component_type_id."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for this component target."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing component display name."),
        ] = None,
        custom_attributes: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Ironbug source field values to place in CustomAttributes, "
                    "for example ReferenceCOP or NominalCapacity; use "
                    "custom_attributes, not ib_properties."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing component with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Add an Ironbug HVAC component."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            component_type=component_type,
            identifier=identifier,
            display_name=display_name,
            custom_attributes=custom_attributes,
            overwrite=overwrite,
        )
