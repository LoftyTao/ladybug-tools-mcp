"""Create Zone Ventilation Fan MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import create_zone_ventilation_fan as service


def register(mcp: FastMCP) -> None:
    """Register the create_zone_ventilation_fan tool."""

    @mcp.tool(
        name="create_zone_ventilation_fan",
        description="Create a Honeybee Energy zone ventilation fan / VentilationFan that exports to EnergyPlus ZoneVentilation:DesignFlowRate. Use this for exhaust fans, intake fans, balanced fans, bathroom/kitchen fans, and fan-assisted zone ventilation. This is mechanical or fan-assisted zone ventilation, not operable-window natural ventilation. In Garden mode, pass garden_root and return_object_dict=false to save directly as a zone_ventilation_fan target for edit_honeybee_room.zone_ventilation_fans.",
        tags={
            "honeybee-energy",
            "garden-mode",
            "zone-ventilation",
            "mechanical-ventilation",
            "ventilation-fan",
            "exhaust-fan",
            "intake-fan",
            "balanced-fan",
            "hvac",
            "write",
            "safe",
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
            Field(description="Optional full Honeybee Energy VentilationControl dict for fan operation."),
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
            Field(description="Optional Garden root. If provided, saves directly to Garden Properties Library."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
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
