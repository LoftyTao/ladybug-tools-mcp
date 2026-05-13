"""Create UWG simulation parameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.parameters import create_uwg_simulation_parameter as service


def register(mcp: FastMCP) -> None:
    """Register the create_uwg_simulation_parameter tool."""

    @mcp.tool(
        name="create_uwg_simulation_parameter",
        description=(
            "Create and optionally save a Dragonfly UWGSimulationParameter for "
            "Alternative Weather workflows. Supports run period, timestep, "
            "vegetation, reference EPW site, and boundary layer settings."
        ),
        tags={
            "run-uwg",
            "uwg",
            "alternative-weather",
            "simulation-parameter",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_uwg_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the saved UWG parameter JSON."),
        ] = None,
        climate_zone: Annotated[
            str | None,
            Field(description="Optional UWG ASHRAE climate zone such as 5A. Defaults to SDK autocalculate."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dict with start_month, start_day, end_month, and end_day."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="UWG timesteps per hour. Default is 12."),
        ] = 12,
        vegetation_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg VegetationParameter dictionary."),
        ] = None,
        reference_epw_site: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg ReferenceEPWSite dictionary."),
        ] = None,
        boundary_layer_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg BoundaryLayerParameter dictionary."),
        ] = None,
        save: Annotated[
            bool,
            Field(description="Save the parameter JSON into Garden artifacts/uwg/parameters."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Return the full parameter dict. Keep False for Agent workflows."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a UWG simulation parameter."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            climate_zone=climate_zone,
            run_period=run_period,
            timestep=timestep,
            vegetation_parameter=vegetation_parameter,
            reference_epw_site=reference_epw_site,
            boundary_layer_parameter=boundary_layer_parameter,
            save=save,
            include_body=include_body,
        )
