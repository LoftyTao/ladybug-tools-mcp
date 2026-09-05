"""Create a reusable Energy SimulationParameter MCP target."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the EP_create_simulation_parameter tool."""

    @mcp.tool(
        name="EP_create_simulation_parameter",
        description=(
            "Create and persist a reusable Honeybee Energy SimulationParameter "
            "target for later EP_start_simulation or EP_run_simulation_wait calls. "
            "Use task-level run_period, design_days strategies, sizing factors, "
            "shadow_calculation settings, and an optional output_request_target; "
            "design-day strategies are resolved from the selected weather DDY "
            "when weather_target is supplied here or at simulation start. Returns "
            "simulation_parameter_target, compact summary_view, "
            "persistence_receipt, and report, without returning the full SDK body "
            "unless include_body=true."
        ),
        tags={"energy", "energyplus", "author", "parameter", "simulation"},
        timeout=20,
    )
    def create_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the saved parameter target."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional task-level period with start_month, start_day, "
                    "end_month, end_day, and optional start_day_of_week/leap_year."
                )
            ),
        ] = None,
        design_days: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional DDY strategies: all, heating, cooling, "
                    "heating_99.6, heating_99, cooling_0.4, cooling_1, "
                    "99.6/0.4, or 99/1."
                )
            ),
        ] = None,
        sizing: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional sizing settings such as heating_factor, cooling_factor, "
                    "efficiency_standard, climate_zone, building_type, and "
                    "bypass_efficiency_sizing."
                )
            ),
        ] = None,
        shadow_calculation: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional EnergyPlus shadow settings such as solar_distribution, "
                    "calculation_method, calculation_update_method, "
                    "calculation_frequency, and maximum_figures."
                )
            ),
        ] = None,
        output_request_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional energy_output_request target returned by "
                    "EP_create_output_request."
                )
            ),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional weather_file target with ddy_path; when supplied, "
                    "design_days strategies are resolved during creation."
                )
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full SDK SimulationParameter dictionary."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a reusable Energy SimulationParameter target."""
        from garden.run_energy.parameters import (
            create_simulation_parameter as service,
        )

        return service(
            garden_root=garden_root,
            identifier=identifier,
            run_period=run_period,
            design_days=design_days,
            sizing=sizing,
            shadow_calculation=shadow_calculation,
            output_request_target=output_request_target,
            weather_target=weather_target,
            include_body=include_body,
        )
