"""Read EPW weather file DataCollections MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.weather_data import read_weather_file_data as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_read_weather_file_data tool.'

    @mcp.tool(
        name='read_weather_file_data',
        description=(
            "Read a Garden-managed EPW weather_file, including UWG morphed "
            "EPW outputs, into a Ladybug DataCollection target with the "
            "Ladybug SDK EPW interface. Use this for weather comparisons such "
            "as dry bulb temperature, relative humidity, wind speed, wind "
            "direction, direct normal radiation, diffuse horizontal radiation, "
            "and global horizontal radiation. This reads weather data, not "
            "EnergyPlus SQL or simulation result data. Provide exactly one of "
            "weather_target or epw_path; epw_path must stay inside the Garden."
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "result",
            "data-collection",
        },
        timeout=60,
    )
    def read_weather_file_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Garden weather_file target returned by energyplus_download_epw, energyplus_search_weather_files, uwg_run_simulation_wait, or uwg_poll_simulation. Provide exactly one of weather_target or epw_path.'
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative or absolute Garden-contained .epw path. Provide exactly one of weather_target or epw_path."
            ),
        ] = None,
        data_type: Annotated[
            str,
            Field(
                description="EPW data field. Examples: dry_bulb_temperature, relative_humidity, wind_speed, wind_direction, direct_normal_radiation, diffuse_horizontal_radiation, global_horizontal_radiation, dew_point_temperature, atmospheric_station_pressure."
            ),
        ] = "dry_bulb_temperature",
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dict or string used to filter the EPW DataCollection before saving, for example '7/21 to 7/21 between 0 and 23 @1'."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional identifier for the saved ladybug_data_collection target. Defaults to weather identifier plus EPW data_type."
            ),
        ] = None,
        include_values: Annotated[
            bool,
            Field(
                description="Whether to include bounded raw values in the compact summary. Default false to keep Agent context small."
            ),
        ] = False,
        max_values: Annotated[
            int,
            Field(description="Maximum weather DataCollection values returned in summary when include_values is true."),
        ] = 24,
        return_data_collection: Annotated[
            bool,
            Field(
                description="Return the full Ladybug DataCollection dict. Keep false for chart workflows and pass data_collection_target downstream."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Read EPW weather data as a Ladybug DataCollection target."""
        return service(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
            data_type=data_type,
            analysis_period=analysis_period,
            identifier=identifier,
            include_values=include_values,
            max_values=max_values,
            return_data_collection=return_data_collection,
        )
