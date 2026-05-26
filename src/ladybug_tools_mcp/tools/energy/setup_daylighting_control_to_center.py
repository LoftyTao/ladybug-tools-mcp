"""Setup Honeybee Energy daylighting controls MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.energy.daylighting import setup_daylighting_control_to_center as service


def register(mcp: FastMCP) -> None:
    'Register the energy_setup_daylighting_control_to_center tool.'

    @mcp.tool(
        name='setup_daylighting_control_to_center',
        description="Assign Honeybee Energy DaylightingControl objects to selected Rooms by placing an EnergyPlus daylight reference sensor near each room center. Use this for electric lighting dimming and lighting-energy impact tests with existing apertures/windows and Lighting loads; it is not a Radiance SensorGrid, glare, sDA, ASE, or daylight-quality simulation. Returns the updated Honeybee model target in target and summary_view.target plus persistence_receipt and report.",
        tags={
            "daylight",
            "daylighting-control",
            "dimming",
            "edit",
            "energy",
            "lighting",
            "room",
        },
        timeout=30,
    )
    def setup_daylighting_control_to_center(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional room_identifiers list to update. Use this or room_targets; not room_target. If omitted with room_targets, all rooms are updated."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Optional room_targets list of Honeybee Room typed targets from honeybee_search_model_objects. Use this or room_identifiers; not room_target.'),
        ] = None,
        distance_from_floor: Annotated[
            float,
            Field(description="Sensor height above room floor in meters, commonly 0.8 m."),
        ] = 0.8,
        illuminance_setpoint: Annotated[
            float,
            Field(description="Illuminance setpoint in lux above which electric lights dim."),
        ] = 300,
        control_fraction: Annotated[
            float,
            Field(description="Fraction of room lighting controlled by the daylight sensor, from 0 to 1."),
        ] = 1.0,
        min_power_input: Annotated[
            float,
            Field(description="Minimum dimmed lighting power fraction, from 0 to 1."),
        ] = 0.3,
        min_light_output: Annotated[
            float,
            Field(description="Minimum dimmed light output fraction, from 0 to 1."),
        ] = 0.2,
        off_at_minimum: Annotated[
            bool,
            Field(description="Whether lights switch fully off after reaching minimum power."),
        ] = False,
        tolerance: Annotated[
            float,
            Field(description="Geometry tolerance in model units for finding a valid room-center sensor point."),
        ] = 0.01,
    ) -> dict[str, Any]:
        """Assign daylighting controls to selected Rooms."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            distance_from_floor=distance_from_floor,
            illuminance_setpoint=illuminance_setpoint,
            control_fraction=control_fraction,
            min_power_input=min_power_input,
            min_light_output=min_light_output,
            off_at_minimum=off_at_minimum,
            tolerance=tolerance,
        )
