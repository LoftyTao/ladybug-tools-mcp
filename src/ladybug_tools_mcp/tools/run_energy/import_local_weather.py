"""Import local weather files into a Garden."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the EP_import_local_weather tool."""

    @mcp.tool(
        name="EP_import_local_weather",
        description=(
            "Copy bundled or local EPW/DDY/STAT weather files into a Garden "
            "imports/weather directory and register it as a weather_file target. "
            "Use weather://files/<station> for a bundled FastMCP weather resource, "
            "or provide an absolute local file/folder path. Use "
            "weather://catalog to list bundled stations before "
            "EP_search_weather_files, UWG, URBANopt, EnergyPlus, or "
            "Radiance weather handoffs. For other locations, obtain an archive from "
            "https://climate.onebuilding.org/, extract it locally, and import it here. "
            "This tool does not download remote files or run simulations."
        ),
        tags={"energy", "weather", "epw", "offline", "garden"},
        timeout=60,
    )
    def import_local_weather(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        source_path: Annotated[
            str,
            Field(
                description=(
                    "Bundled weather resource URI weather://files/<station>, or an "
                    "absolute local .epw file path or folder containing EPW/DDY/STAT files."
                ),
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable weather identifier for the Garden target."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Overwrite an existing imported weather folder with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Import local weather files and return a weather_file target."""
        from garden.run_energy.config import import_local_weather_folder as service

        return service(
            garden_root=garden_root,
            source_path=source_path,
            identifier=identifier,
            overwrite=overwrite,
        )
