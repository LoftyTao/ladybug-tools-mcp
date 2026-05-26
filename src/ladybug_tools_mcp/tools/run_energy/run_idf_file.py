"""Run edited IDF file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.files import run_idf_file as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_run_idf_file tool.'

    @mcp.tool(
        name='run_idf_file',
        description=(
            "Run a user-edited EnergyPlus IDF file inside a Garden with the "
            "Ladybug Tools Grasshopper file-run pattern. Use this after a user "
            "edits IDF algorithms, EMS, HVAC templates, or other EnergyPlus "
            "objects. This is a blocking file run and does not author a "
            "Honeybee model. Returns run_target, energy_run_target, "
            "runtime_status through summary_view.status, and report."
        ),
        tags={
            "energy",
            "simulate",
            "idf",
            "file",
            "blocking",
        },
        timeout=3600,
    )
    def run_idf_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        idf_path: Annotated[
            str,
            Field(
                description=(
                    "Garden-relative or Garden-contained absolute path to the "
                    "edited .idf file."
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
                    "Optional Garden-relative EPW path. Omit only for "
                    "design-day-only IDF simulations."
                )
            ),
        ] = None,
        expand_objects: Annotated[
            bool,
            Field(
                description=(
                    "Expand EnergyPlus HVAC Template objects before simulation."
                )
            ),
        ] = True,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable EnergyPlus IDF run identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run EnergyPlus silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Run an IDF file and register an energy_run target."""
        return service(
            garden_root=garden_root,
            idf_path=idf_path,
            weather_target=weather_target,
            epw_path=epw_path,
            expand_objects=expand_objects,
            run_id=run_id,
            silent=silent,
        )
