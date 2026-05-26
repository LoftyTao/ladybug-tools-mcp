"""Create Electric Load Center MCP tool."""

from __future__ import annotations
from typing import Annotated
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import create_electric_load_center as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_electric_load_center tool.'

    @mcp.tool(
        name='create_electric_load_center',
        description=(
            "Create Honeybee Energy ElectricLoadCenter model-level settings "
            "for photovoltaic inverter efficiency and DC-to-AC sizing. Use this "
            "with energy_create_pv_properties on Honeybee Shades, then assign "
            "the saved electric_load_center target through "
            "honeybee_edit_model.electric_load_center. This Honeybee Energy "
            "object is separate from Ironbug electric load center objects and "
            "does not start an EnergyPlus run."
        ),
        tags={
            "energy",
            "model",
            "author",
            "load-center",
        },
        timeout=20,
    )
    def create_electric_load_center(
        identifier: Annotated[
            str,
            Field(description="Identifier used for the Garden Properties Library target. The Honeybee ElectricLoadCenter object itself is model-level and has no identifier."),
        ] = "electric_load_center",
        inverter_efficiency: Annotated[
            float,
            Field(description="Inverter nominal DC-to-AC conversion efficiency from 0 to 1."),
        ] = 0.96,
        inverter_dc_to_ac_size_ratio: Annotated[
            float,
            Field(description="Ratio of inverter DC rated size to AC rated size."),
        ] = 1.1,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
        ] = True,
    ) -> dict:
        """Create electric load center settings."""
        return service(
            identifier=identifier,
            inverter_efficiency=inverter_efficiency,
            inverter_dc_to_ac_size_ratio=inverter_dc_to_ac_size_ratio,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
