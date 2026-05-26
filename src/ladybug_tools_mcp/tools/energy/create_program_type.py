"""Create ProgramType MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_program_type as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_program_type tool.'

    @mcp.tool(
        name='create_program_type',
        description="Create a Honeybee Energy ProgramType, the room program bundle for occupancy, lighting, equipment, service hot water, infiltration, ventilation, and setpoints. ProgramType is an upstream Honeybee Energy abstraction that later expands to multiple EnergyPlus loads and schedules; it is not one EnergyPlus object. Prefer Garden Properties Library targets from load creation tools with garden_root and return_object_dict=false. Returns object_dict, or target plus persistence_receipt when saved.",
        tags={
            "energy",
            "program-type",
            "load",
            "occupancy",
            "schedule",
            "author",
        },
        timeout=20,
    )
    def create_program_type(
        identifier: Annotated[str, Field(description="ProgramType identifier.")],
        base_program_type: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional base ProgramType dict, Garden Properties Library target, or ProgramType library identifier."
            ),
        ] = None,
        people: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional People object_dict or Garden Properties Library load target."
            ),
        ] = None,
        lighting: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Lighting object_dict or Garden Properties Library load target."
            ),
        ] = None,
        electric_equipment: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ElectricEquipment object_dict or Garden Properties Library load target."
            ),
        ] = None,
        gas_equipment: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional GasEquipment object_dict or Garden Properties Library load target."
            ),
        ] = None,
        service_hot_water: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ServiceHotWater object_dict or Garden Properties Library load target."
            ),
        ] = None,
        infiltration: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Infiltration object_dict or Garden Properties Library load target."
            ),
        ] = None,
        ventilation: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ventilation object_dict or Garden Properties Library load target."
            ),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Setpoint object_dict or Garden Properties Library load target."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full ProgramType object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ProgramType object."""
        return service(
            identifier=identifier,
            base_program_type=base_program_type,
            people=people,
            lighting=lighting,
            electric_equipment=electric_equipment,
            gas_equipment=gas_equipment,
            service_hot_water=service_hot_water,
            infiltration=infiltration,
            ventilation=ventilation,
            setpoint=setpoint,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
