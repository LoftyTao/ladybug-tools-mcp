"""Create Energy output request MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.output_requests import (
    create_energy_output_request as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energyplus_create_output_request tool.'

    @mcp.tool(
        name="create_output_request",
        description=(
            "Create a Garden energy_output_request target for EnergyPlus "
            "outputs before an energy run. Use it for hourly zone loads, HVAC "
            "energy use, unmet hours, surface temperatures, custom "
            "Output:Variable names, summary reports, or later result "
            "visualization. Pass the returned target to "
            "energyplus_start_simulation or energyplus_run_simulation_wait as "
            "output_request_target. This tool prepares requests; it does not "
            "read SQL, ERR, HTML, or DataCollection results."
        ),
        tags={
            "energy",
            "result",
            "sql",
            "author",
            "report",
        },
        timeout=20,
    )
    def create_energy_output_request(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for this energy_output_request target."),
        ],
        presets: Annotated[
            list[str] | None,
            Field(
                description="Optional named output presets such as zone_energy_use, hvac_energy_use, unmet_hours, surface_temperature, surface_energy_flow, glazing_solar, comfort_metrics, energy_balance, gains_and_losses, or electricity_generation."
            ),
        ] = None,
        custom_outputs: Annotated[
            list[str] | None,
            Field(
                description="Optional exact EnergyPlus Output:Variable names to request, for example Facility Total HVAC Electricity Demand Rate."
            ),
        ] = None,
        summary_reports: Annotated[
            list[str] | None,
            Field(
                description="Optional EnergyPlus summary reports, for example AllSummary or AnnualBuildingUtilityPerformanceSummary."
            ),
        ] = None,
        reporting_frequency: Annotated[
            str,
            Field(
                description="EnergyPlus reporting frequency for output variables: Annual, Monthly, Daily, Hourly, or Timestep."
            ),
        ] = "Hourly",
        include_sqlite: Annotated[
            bool,
            Field(
                description="Whether the simulation should write a SQLite result file for DataCollection result reading."
            ),
        ] = True,
        include_html: Annotated[
            bool,
            Field(description="Whether the simulation should write an HTML summary report."),
        ] = True,
        unmet_setpoint_tolerance: Annotated[
            float,
            Field(description="Unmet setpoint tolerance in degrees Celsius."),
        ] = 1.11,
    ) -> dict[str, Any]:
        """Create an Energy output request target."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            presets=presets,
            custom_outputs=custom_outputs,
            summary_reports=summary_reports,
            reporting_frequency=reporting_frequency,
            include_sqlite=include_sqlite,
            include_html=include_html,
            unmet_setpoint_tolerance=unmet_setpoint_tolerance,
        )
