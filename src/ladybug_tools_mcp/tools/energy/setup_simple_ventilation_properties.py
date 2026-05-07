"""Setup simple Honeybee Energy ventilation properties MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import (
    setup_simple_ventilation_properties as service,
)


def register(mcp: FastMCP) -> None:
    """Register the setup_simple_ventilation_properties tool."""

    @mcp.tool(
        name="setup_simple_ventilation_properties",
        description="Apply simple operable-window natural ventilation properties to Honeybee Rooms in a Garden model. Use this for natural ventilation, operable windows, window opening area, cross ventilation, and ventilative cooling control. This is the simple path: it sets room window_vent_control and aperture/door vent_opening properties, but does not generate AirflowNetwork cracks and does not create zone ventilation fans. Select rooms with room_identifiers or room_targets; not room_target, not opening_area, and not opening_fraction.",
        tags={
            "honeybee-energy",
            "garden-mode",
            "natural-ventilation",
            "simple-ventilation",
            "operable-window",
            "window-vent-control",
            "ventilation-opening",
            "ventilative-cooling",
            "write",
            "safe",
        },
        timeout=30,
    )
    def setup_simple_ventilation_properties(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional room_identifiers list to update. Use this or room_targets; not room_target. If omitted with room_targets, all model rooms are updated."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional room_targets list of Honeybee Room typed targets from search_honeybee_model_objects. Use this or room_identifiers; not room_target."),
        ] = None,
        fraction_area_operable: Annotated[
            float,
            Field(description="Fraction of window area that is operable, from 0 to 1. This is the operable area field; not opening_area and not opening_fraction."),
        ] = 0.5,
        fraction_height_operable: Annotated[
            float,
            Field(description="Fraction of window height that is operable, from 0 to 1."),
        ] = 1.0,
        discharge_coefficient: Annotated[
            float,
            Field(description="Opening discharge coefficient, commonly 0.45 with insect screens or 0.65 without screens."),
        ] = 0.45,
        wind_cross_vent: Annotated[
            bool,
            Field(description="Whether wind-driven cross ventilation is expected."),
        ] = False,
        flow_coefficient_closed: Annotated[
            float,
            Field(description="Closed-opening AFN leakage coefficient. Keep 0 for simple non-AFN ventilation."),
        ] = 0,
        flow_exponent_closed: Annotated[
            float,
            Field(description="Closed-opening AFN leakage exponent."),
        ] = 0.65,
        two_way_threshold: Annotated[
            float,
            Field(description="AFN two-way flow density threshold for openings."),
        ] = 0.0001,
        min_indoor_temperature: Annotated[
            float,
            Field(description="Minimum indoor temperature in Celsius at which ventilation can occur."),
        ] = -100,
        max_indoor_temperature: Annotated[
            float,
            Field(description="Maximum indoor temperature in Celsius at which ventilation can occur."),
        ] = 100,
        min_outdoor_temperature: Annotated[
            float,
            Field(description="Minimum outdoor temperature in Celsius at which ventilation can occur."),
        ] = -100,
        max_outdoor_temperature: Annotated[
            float,
            Field(description="Maximum outdoor temperature in Celsius at which ventilation can occur."),
        ] = 100,
        delta_temperature: Annotated[
            float,
            Field(description="Indoor minus outdoor temperature threshold in Celsius for ventilative cooling."),
        ] = -100,
    ) -> dict[str, Any]:
        """Apply simple natural ventilation properties."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            fraction_area_operable=fraction_area_operable,
            fraction_height_operable=fraction_height_operable,
            discharge_coefficient=discharge_coefficient,
            wind_cross_vent=wind_cross_vent,
            flow_coefficient_closed=flow_coefficient_closed,
            flow_exponent_closed=flow_exponent_closed,
            two_way_threshold=two_way_threshold,
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
        )
