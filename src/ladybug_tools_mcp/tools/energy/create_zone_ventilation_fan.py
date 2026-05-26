"""Create Zone Ventilation Fan MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import create_zone_ventilation_fan as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_zone_ventilation_fan tool.'

    @mcp.tool(
        name='create_zone_ventilation_fan',
        description='Create a Honeybee Energy VentilationFan for fan-assisted zone ventilation or ventilative cooling with Exhaust, Intake, or Balanced outdoor-air flow. Use garden_root to save a zone_ventilation_fan target for honeybee_edit_room.zone_ventilation_fans; set return_object_dict=false only when you want a compact target/summary/receipt response. This exports to EnergyPlus ZoneVentilation:DesignFlowRate and is not the ProgramType Ventilation load, Infiltration, operable-window natural ventilation, AirflowNetwork, or Ironbug DetailedHVAC fan component.',
        tags={
            "author",
            "energy",
            "fan",
            "outdoor-air",
            "ventilation",
            "ventilation-fan",
            "ventilative-cooling",
            "zone-exhaust",
        },
        timeout=20,
    )
    def create_zone_ventilation_fan(
        identifier: Annotated[
            str,
            Field(description="Unique VentilationFan identifier."),
        ],
        flow_rate: Annotated[
            float,
            Field(description="Fan air flow rate in m3/s."),
        ],
        ventilation_type: Annotated[
            str,
            Field(description="Zone ventilation type: Exhaust, Intake, or Balanced."),
        ] = "Balanced",
        pressure_rise: Annotated[
            float | None,
            Field(description="Optional fan pressure rise in Pascals. If omitted, SDK estimates from flow rate."),
        ] = None,
        efficiency: Annotated[
            float | None,
            Field(description="Optional total fan efficiency from 0 to 1. If omitted, SDK estimates from flow and pressure."),
        ] = None,
        control: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Energy VentilationControl object_dict for fan operation; omit it to build a control from the temperature threshold fields."),
        ] = None,
        min_indoor_temperature: Annotated[
            float,
            Field(description="Minimum indoor temperature in Celsius at which the fan can operate."),
        ] = -100,
        max_indoor_temperature: Annotated[
            float,
            Field(description="Maximum indoor temperature in Celsius at which the fan can operate."),
        ] = 100,
        min_outdoor_temperature: Annotated[
            float,
            Field(description="Minimum outdoor temperature in Celsius at which the fan can operate."),
        ] = -100,
        max_outdoor_temperature: Annotated[
            float,
            Field(description="Maximum outdoor temperature in Celsius at which the fan can operate."),
        ] = 100,
        delta_temperature: Annotated[
            float,
            Field(description="Indoor minus outdoor temperature threshold in Celsius for fan operation."),
        ] = -100,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to omit object_dict and return only compact target, summary_view, persistence_receipt, and report."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a zone ventilation fan."""
        return service(
            identifier=identifier,
            flow_rate=flow_rate,
            ventilation_type=ventilation_type,
            pressure_rise=pressure_rise,
            efficiency=efficiency,
            control=control,
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
