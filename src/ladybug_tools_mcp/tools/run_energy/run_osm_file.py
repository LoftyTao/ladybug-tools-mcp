"""Run edited OSM file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.files import run_osm_file as service


def register(mcp: FastMCP) -> None:
    """Register the run_osm_file tool."""

    @mcp.tool(
        name="run_osm_file",
        description=(
            "Run a user-edited OpenStudio .osm file inside a Garden. The tool "
            "deterministically creates or updates a persistent workflow.osw beside "
            "the OSM file, then runs OpenStudio with measures_only=false so "
            "OpenStudio/EnergyPlus outputs stay in the OSM folder's run directory. "
            "Use this after an Agent or user modifies an OSM for HVAC or other "
            "OpenStudio-level edits."
        ),
        tags={
            "run-energy",
            "energy",
            "openstudio",
            "osm",
            "osw",
            "energyplus",
            "file-run",
            "write",
            "safe",
        },
        timeout=3600,
    )
    def run_osm_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
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
                    "Optional Garden weather_file target returned by download_epw "
                    "or search_weather_files. Use instead of epw_path."
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
            Field(description="Optional stable run identifier. Omit to generate one."),
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
