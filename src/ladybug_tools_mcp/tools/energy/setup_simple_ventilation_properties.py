"""Setup simple Honeybee Energy ventilation properties MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import (
    setup_simple_ventilation_properties as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_setup_simple_ventilation_properties tool.'

    @mcp.tool(
        name='setup_simple_ventilation_properties',
        description="Apply simple operable-window natural ventilation properties to Honeybee Rooms in a Garden model. Use this for VentilationOpening, window_vent_control, operable windows, cross ventilation, and ventilative cooling controls; it does not generate AirflowNetwork cracks and does not create VentilationFan objects. Returns the updated Honeybee model target in target and summary_view.target plus persistence_receipt and report.",
        tags={
            "cross-ventilation",
            "edit",
            "energy",
            "natural-ventilation",
            "operable-window",
            "room",
            "ventilation",
            "ventilation-opening",
            "ventilative-cooling",
        },
        timeout=30,
    )
    def setup_simple_ventilation_properties(
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
            Field(description="Optional room_identifiers list to update. Use this or room_targets; not room_target. If omitted with room_targets, all model rooms are updated."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Optional room_targets list of Honeybee Room typed targets from honeybee_search_model_objects. Use this or room_identifiers; not room_target.'),
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
            Field(description="Closed-opening AirflowNetwork leakage coefficient. Keep 0 for the simple non-AFN ventilation path."),
        ] = 0,
        flow_exponent_closed: Annotated[
            float,
            Field(description="Closed-opening AirflowNetwork leakage exponent used only if the opening later participates in AFN."),
        ] = 0.65,
        two_way_threshold: Annotated[
            float,
            Field(description="AirflowNetwork two-way flow density threshold for openings, used only when AFN is enabled."),
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
