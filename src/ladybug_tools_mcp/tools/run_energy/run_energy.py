"""Run Energy simulation MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import run_energy as service


def register(mcp: FastMCP) -> None:
    """Register the run_energy tool."""

    @mcp.tool(
        name="run_energy",
        description="Blocking/local Honeybee Energy annual-energy-use recipe run for a Garden Honeybee model with Garden-managed EPW/DDY weather. This can take many minutes and should not be the default Agent path. Agents and Code Mode workflows should prefer start_energy_run with a weather_target from download_epw/search_weather_files, then poll get_energy_run and read outputs. This blocking tool writes results under runs/energy/<run_id>, records an energy_run target, and returns only a lightweight output index instead of large SQL, HTML, ZSZ, or ERR contents.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "annual-energy-use",
            "epw",
            "ddy",
            "recipe",
            "write",
            "safe",
        },
        timeout=3600,
    )
    def run_energy(
        garden_root: Annotated[
            str, Field(description="Garden root containing garden.json.")
        ],
        epw_path: Annotated[
            str | None,
            Field(
                description="Garden-relative EPW path fallback for controlled tests. Agents should pass the Garden weather_file target instead."
            ),
        ] = None,
        ddy_path: Annotated[
            str | None,
            Field(
                description="Garden-relative DDY path fallback for controlled tests. Agents should pass the Garden weather_file target instead."
            ),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Garden-managed weather_file target returned by download_epw or search_weather_files."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target. Defaults to the Garden base model."
            ),
        ] = None,
        sim_par: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy SimulationParameter dictionary. Saved to the run inputs folder."
            ),
        ] = None,
        output_request_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional parameter named exactly output_request_target. Pass the energy_output_request target returned by create_energy_output_request. It is merged into the SimulationParameter output section and recorded in the run ledger."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        units: Annotated[
            str, Field(description="EUI units for result summaries: si or ip.")
        ] = "si",
        workers: Annotated[
            int | None, Field(description="Optional recipe worker count.")
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description="Reload existing recipe results for the run folder when available."
            ),
        ] = False,
        silent: Annotated[
            bool, Field(description="Run OpenStudio/EnergyPlus silently.")
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(
                description="Validate EPW/DDY with the Ladybug SDK before launching the long recipe."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Run annual energy-use simulation and register an energy_run target."""
        return service(
            garden_root=garden_root,
            epw_path=epw_path,
            ddy_path=ddy_path,
            weather_target=weather_target,
            model_target=model_target,
            sim_par=sim_par,
            output_request_target=output_request_target,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )
