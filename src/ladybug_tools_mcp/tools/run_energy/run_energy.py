"""Run Energy simulation MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import run_energy as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_run_simulation_wait tool.'

    @mcp.tool(
        name="run_simulation_wait",
        description=(
            "Run the blocking Honeybee Energy annual-energy-use recipe for a "
            "Garden Honeybee model with Garden-managed EPW/DDY weather. Use "
            "energyplus_start_simulation plus energyplus_poll_simulation for "
            "the normal nonblocking workflow. Advanced users can pass "
            "Garden-local additional_idf_path, inline additional_idf_text, or "
            "measures_path. This tool writes runs/energy/<run_id>, records an "
            "energy_run target, and returns runtime_status through "
            "summary_view.status plus a lightweight output index. Treat failed "
            "runtime_status as requiring report review."
        ),
        tags={
            "energy",
            "simulate",
            "epw",
            "poll",
            "blocking",
        },
        timeout=3600,
    )
    def run_energy(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Garden weather file target returned by energyplus_download_epw or a Garden-relative EPW path.'
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
                description='Optional parameter named exactly output_request_target. Pass the energy_output_request target returned by energyplus_create_output_request. It is merged into the SimulationParameter output section and recorded in the run ledger.'
            ),
        ] = None,
        additional_idf_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an additional EnergyPlus .idf file. Advanced users can use this to append supported EnergyPlus objects before simulation; the file must stay inside the Garden."
            ),
        ] = None,
        additional_idf_text: Annotated[
            str | None,
            Field(
                description="Optional inline additional EnergyPlus IDF text. Advanced users can pass small complete EnergyPlus objects such as EMS snippets; the service saves the text into the run inputs folder and passes it as recipe additional-idf. Do not pass this together with additional_idf_path."
            ),
        ] = None,
        measures_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an OpenStudio measures folder for the annual-energy-use recipe. The folder must stay inside the Garden and contain the OSW JSON plus referenced measures."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        units: Annotated[
            str, Field(description="EUI units for EnergyPlus result summaries: si or ip.")
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
            weather_target=weather_target,
            model_target=model_target,
            sim_par=sim_par,
            output_request_target=output_request_target,
            additional_idf_path=additional_idf_path,
            additional_idf_text=additional_idf_text,
            measures_path=measures_path,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )
