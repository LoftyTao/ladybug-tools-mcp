"""Create IdealAirSystem MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.hvac import create_ideal_air_system as service


def register(mcp: FastMCP) -> None:
    """Register the create_ideal_air_system tool."""

    @mcp.tool(
        name="create_ideal_air_system",
        description="Create a Honeybee Energy IdealAirSystem HVAC object for a simple HVAC choice, compact office conditioning, early-stage room energy properties, or program/setpoint assignment workflows. Returns a full object_dict, or saves to Garden Properties Library and returns a target when garden_root is provided. For a simple HVAC, omit heating_air_temperature_ and cooling_air_temperature_; they are supply air temperatures, not room setpoints.",
        tags={
            "honeybee-energy",
            "energy",
            "hvac",
            "simple-hvac",
            "office-hvac",
            "ideal-air",
            "room-conditioning",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_ideal_air_system(
        identifier: Annotated[str, Field(description="IdealAirSystem identifier.")],
        economizer_type: Annotated[
            str | None,
            Field(
                description="Optional economizer type: NoEconomizer, DifferentialDryBulb, or DifferentialEnthalpy."
            ),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | None,
            Field(description="Optional demand controlled ventilation flag."),
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
        heating_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional maximum heating supply air temperature in C. Must be greater than cooling_air_temperature_; omit for simple HVAC."
            ),
        ] = None,
        cooling_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional minimum cooling supply air temperature in C. Must be less than heating_air_temperature_; omit for simple HVAC."
            ),
        ] = None,
        heating_limit: Annotated[
            float | str | None,
            Field(
                description="Optional heating capacity in W, 'autosize', or 'no_limit'."
            ),
        ] = None,
        cooling_limit: Annotated[
            float | str | None,
            Field(
                description="Optional cooling capacity in W, 'autosize', or 'no_limit'."
            ),
        ] = None,
        heating_availability: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional heating availability schedule dict or library identifier."
            ),
        ] = None,
        cooling_availability: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional cooling availability schedule dict or library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root. When provided, save the HVAC as a reusable Garden Properties Library hvac object."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Whether to include the full SDK object_dict in the response. Use false for low-token Agent Garden workflows."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy IdealAirSystem HVAC object."""
        return service(
            identifier=identifier,
            economizer_type=economizer_type,
            demand_controlled_ventilation=demand_controlled_ventilation,
            sensible_heat_recovery=sensible_heat_recovery,
            latent_heat_recovery=latent_heat_recovery,
            heating_air_temperature=heating_air_temperature,
            cooling_air_temperature=cooling_air_temperature,
            heating_limit=heating_limit,
            cooling_limit=cooling_limit,
            heating_availability=heating_availability,
            cooling_availability=cooling_availability,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
