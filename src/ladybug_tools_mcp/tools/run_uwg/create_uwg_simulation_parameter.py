"""Create UWG simulation parameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.parameters import create_uwg_simulation_parameter as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_create_simulation_parameter tool.'

    @mcp.tool(
        name='create_simulation_parameter',
        description=(
            "Create and optionally save a Dragonfly UWGSimulationParameter for "
            "Alternative Weather workflows. Use this before uwg_dragonfly_model_to_uwg, "
            "uwg_start_simulation, or uwg_run_simulation_wait when custom run period, "
            "timestep, vegetation, reference EPW site, or boundary layer settings are "
            "needed. Returns target, summary_view, persistence_receipt, and report when "
            "saved; it does not run UWG."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "author",
            "parameter",
        },
        timeout=20,
    )
    def create_uwg_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the saved UWGSimulationParameter JSON target."),
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
            Field(description="Return the full UWGSimulationParameter dict. Keep False for compact target handoff."),
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
