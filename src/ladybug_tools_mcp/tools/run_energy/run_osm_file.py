"""Run edited OSM file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.files import run_osm_file as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_run_osm_file tool.'

    @mcp.tool(
        name='run_osm_file',
        description=(
            "Run a user-edited OpenStudio OSM file inside a Garden by creating "
            "or updating workflow.osw beside the OSM file. Use this after "
            "OpenStudio-level HVAC or measure edits. This is a blocking file "
            "run and does not author a Honeybee model. Returns run_target, "
            "energy_run_target, runtime_status through summary_view.status, "
            "and report."
        ),
        tags={
            "energy",
            "simulate",
            "openstudio",
            "osm",
            "blocking",
        },
        timeout=3600,
    )
    def run_osm_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        osm_path: Annotated[
            str,
            Field(
                description=(
                    "Garden-relative or Garden-contained absolute path to the "
                    "edited .osm file."
                )
            ),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Garden weather_file target returned by energyplus_download_epw '
                    'or energyplus_search_weather_files. Use instead of epw_path.'
                )
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative EPW path. Use instead of weather_target."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable OpenStudio OSM run identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run OpenStudio/EnergyPlus silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Run an OSM file and register an energy_run target."""
        return service(
            garden_root=garden_root,
            osm_path=osm_path,
            weather_target=weather_target,
            epw_path=epw_path,
            run_id=run_id,
            silent=silent,
        )
