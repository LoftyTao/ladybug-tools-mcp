"""Search and instantiate HVAC template MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.hvac import search_hvac_templates as service


def register(mcp: FastMCP) -> None:
    """Register the search_hvac_templates tool."""

    @mcp.tool(
        name="search_hvac_templates",
        description="Search Honeybee Energy SDK HVAC templates and, when identifier is provided with a unique template selection, return a ready-to-use HVAC object_dict or Garden Properties Library target for edit_honeybee_room hvac. Supports all-air, DOAS, and heat-cool template HVAC systems.",
        tags={
            "honeybee-energy",
            "energy",
            "hvac",
            "template-hvac",
            "search",
            "create",
            "safe",
        },
        timeout=20,
    )
    def search_hvac_templates(
        query: Annotated[
            str | None,
            Field(
                description="Optional search text such as 'psz packaged single zone', 'vav', 'radiant doas', or 'vrf'."
            ),
        ] = None,
        system_type: Annotated[
            str | None,
            Field(
                description="Optional exact SDK HVAC template type, such as PSZ, VAV, PTAC, FCUwithDOAS, Radiant, or VRF."
            ),
        ] = None,
        family: Annotated[
            str | None,
            Field(
                description="Optional family filter: allair, doas, heatcool, or all."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional identifier. When provided with a unique template, the tool creates an HVAC object_dict."
            ),
        ] = None,
        vintage: Annotated[
            str | None,
            Field(description="Optional template vintage, such as ASHRAE_2019."),
        ] = None,
        equipment_type: Annotated[
            str | None,
            Field(
                description="Optional SDK equipment_type for the selected HVAC template."
            ),
        ] = None,
        economizer_type: Annotated[
            str | None,
            Field(
                description="Optional economizer type for templates that support it."
            ),
        ] = None,
        sensible_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional sensible heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        latent_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional latent heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | None,
            Field(description="Optional demand controlled ventilation flag."),
        ] = None,
        doas_availability_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DOAS availability schedule dict or library identifier for DOAS templates."
            ),
        ] = None,
        radiant_type: Annotated[
            str | None,
            Field(
                description="Optional radiant type for radiant templates, such as Floor or Ceiling."
            ),
        ] = None,
        minimum_operation_time: Annotated[
            float | None,
            Field(description="Optional radiant minimum operation time in hours."),
        ] = None,
        switch_over_time: Annotated[
            float | None,
            Field(description="Optional radiant switch-over time in hours."),
        ] = None,
        return_object: Annotated[
            bool,
            Field(
                description="Whether to create object_dict when identifier and a unique template are available."
            ),
        ] = True,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root. When provided, save the created HVAC as a reusable Garden Properties Library hvac object."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Whether to include the full SDK object_dict in the response after creation. Use false for low-token Agent Garden workflows."
            ),
        ] = True,
        limit: Annotated[
            int, Field(description="Maximum number of template matches to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Energy HVAC templates and optionally create one."""
        return service(
            query=query,
            system_type=system_type,
            family=family,
            identifier=identifier,
            vintage=vintage,
            equipment_type=equipment_type,
            economizer_type=economizer_type,
            sensible_heat_recovery=sensible_heat_recovery,
            latent_heat_recovery=latent_heat_recovery,
            demand_controlled_ventilation=demand_controlled_ventilation,
            doas_availability_schedule=doas_availability_schedule,
            radiant_type=radiant_type,
            minimum_operation_time=minimum_operation_time,
            switch_over_time=switch_over_time,
            return_object=return_object,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
            limit=limit,
        )
