"""Run edited IDF file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.files import run_idf_file as service


def register(mcp: FastMCP) -> None:
    """Register the run_idf_file tool."""

    @mcp.tool(
        name="run_idf_file",
        description=(
            "Run a user-edited EnergyPlus .idf file inside a Garden. This follows "
            "Ladybug Tools Grasshopper behavior: if the input is already named "
            "in.idf it runs in that folder; otherwise the file is copied to a "
            "sibling run/in.idf folder and EnergyPlus runs there. Use this after "
            "an Agent or user modifies IDF algorithms, EMS, HVAC templates, or "
            "other EnergyPlus-level objects."
        ),
        tags={
            "run-energy",
            "energy",
            "energyplus",
            "idf",
            "file-run",
            "write",
            "safe",
        },
        timeout=3600,
    )
    def run_idf_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
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
                    "Optional Garden weather_file target returned by download_epw "
                    "or search_weather_files. Use instead of epw_path."
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
            Field(description="Optional stable run identifier. Omit to generate one."),
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
