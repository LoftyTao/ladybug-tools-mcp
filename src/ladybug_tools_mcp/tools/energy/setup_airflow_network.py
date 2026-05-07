"""Setup Honeybee Energy AirflowNetwork MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import setup_airflow_network as service


def register(mcp: FastMCP) -> None:
    """Register the setup_airflow_network tool."""

    @mcp.tool(
        name="setup_airflow_network",
        description="Generate EnergyPlus AirflowNetwork properties for Honeybee Rooms in a Garden model. Use this for AFN, AirflowNetwork, airflow network, multizone air flow, leakage, cracks, pressure-driven ventilation, and closed-window leakage. This top-level tool sets model ventilation_simulation_control and uses the Honeybee Energy SDK AFN generator to create face vent_crack and opening leakage properties. This is not the simple operable-window path; use setup_simple_ventilation_properties for simple natural ventilation controls.",
        tags={
            "honeybee-energy",
            "garden-mode",
            "airflow-network",
            "afn",
            "multizone-airflow",
            "leakage",
            "vent-crack",
            "ventilation-simulation-control",
            "natural-ventilation",
            "write",
            "safe",
        },
        timeout=30,
    )
    def setup_airflow_network(
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
            Field(description="Optional room identifiers that make up the AirflowNetwork. If omitted with room_targets, all model rooms are used."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Honeybee Room typed targets from search_honeybee_model_objects."),
        ] = None,
        vent_control_type: Annotated[
            str,
            Field(description="Ventilation simulation type: SingleZone, MultiZoneWithDistribution, or MultiZoneWithoutDistribution."),
        ] = "MultiZoneWithoutDistribution",
        leakage_type: Annotated[
            str,
            Field(description="Leakiness template for generated cracks: Excellent, Medium, or VeryPoor."),
        ] = "Medium",
        use_room_infiltration: Annotated[
            bool,
            Field(description="If true, exterior AFN leakage is derived from each room infiltration load when available."),
        ] = True,
        atmospheric_pressure: Annotated[
            float,
            Field(description="Atmospheric pressure in Pascals used for dry-air density."),
        ] = 101325,
        delta_pressure: Annotated[
            float,
            Field(description="Reference pressure difference in Pascals for infiltration-derived cracks."),
        ] = 4,
        reference_temperature: Annotated[
            float,
            Field(description="AFN reference temperature in Celsius."),
        ] = 20,
        reference_pressure: Annotated[
            float,
            Field(description="AFN reference pressure in Pascals."),
        ] = 101325,
        reference_humidity_ratio: Annotated[
            float,
            Field(description="AFN reference humidity ratio in kgWater/kgDryAir."),
        ] = 0,
        building_type: Annotated[
            str,
            Field(description="AFN building type: LowRise or HighRise."),
        ] = "LowRise",
        long_axis_angle: Annotated[
            float,
            Field(description="Clockwise angle in degrees from true North for the building long axis."),
        ] = 0,
        aspect_ratio: Annotated[
            float,
            Field(description="Building footprint aspect ratio used by AFN wind pressure coefficients."),
        ] = 1,
        autocalculate_geometry_properties: Annotated[
            bool,
            Field(description="If true, derive AFN building geometry properties from the selected rooms."),
        ] = True,
    ) -> dict[str, Any]:
        """Generate AirflowNetwork properties."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            vent_control_type=vent_control_type,
            leakage_type=leakage_type,
            use_room_infiltration=use_room_infiltration,
            atmospheric_pressure=atmospheric_pressure,
            delta_pressure=delta_pressure,
            reference_temperature=reference_temperature,
            reference_pressure=reference_pressure,
            reference_humidity_ratio=reference_humidity_ratio,
            building_type=building_type,
            long_axis_angle=long_axis_angle,
            aspect_ratio=aspect_ratio,
            autocalculate_geometry_properties=autocalculate_geometry_properties,
        )
