"""Start Energy simulation MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import start_energy_run as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_start_simulation tool.'

    @mcp.tool(
        name="start_simulation",
        description=(
            "Start a nonblocking annual Honeybee Energy annual-energy-use "
            "simulation for a Garden Honeybee model with Garden-managed "
            "EPW/DDY weather. Pass weather_target from energyplus_download_epw "
            "or energyplus_search_weather_files plus an optional Honeybee "
            "model target. Returns run_target, energy_run_target, "
            "runtime_status through summary_view.status, poll_next, and "
            "report. Poll with energyplus_poll_simulation before reading "
            "result artifacts. Treat failed runtime_status as requiring "
            "report review."
        ),
        tags={
            "energy",
            "simulate",
            "epw",
            "poll",
            "start",
        },
        timeout=60,
    )
    def start_energy_run(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Garden weather file target returned by energyplus_download_epw or a Garden-relative EPW path. Keep the full target with epw_path and ddy_path when possible; registered identifier/path-only targets can be rehydrated from garden.json.'
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model."
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
                description="Reload existing recipe results for the run folder when available. With a finished Garden run ledger and matching run_id, return the existing energy_run target without starting a new background run."
            ),
        ] = False,
        silent: Annotated[
            bool, Field(description="Run OpenStudio/EnergyPlus silently.")
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(
                description="Validate EPW/DDY with the Ladybug SDK before launching the background recipe."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Start annual energy-use simulation and return an energy_run target."""
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
