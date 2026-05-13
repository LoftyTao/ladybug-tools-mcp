"""Read EPW weather file DataCollections MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.weather_data import read_weather_file_data as service


def register(mcp: FastMCP) -> None:
    """Register the read_weather_file_data tool."""

    @mcp.tool(
        name="read_weather_file_data",
        description="Read a Garden-managed EPW weather_file, including UWG morphed EPW outputs, into a Ladybug DataCollection target using the Ladybug SDK EPW interface. Use this before data_collection_monthly_chart_to_visualization_set or data_collection_hourly_plot_to_visualization_set for weather comparisons such as dry bulb temperature, relative humidity, wind speed, wind direction, direct normal radiation, diffuse horizontal radiation, and global horizontal radiation. Provide exactly one of weather_target or epw_path; epw_path must stay inside the Garden. Optional analysis_period accepts a Ladybug AnalysisPeriod dict or string such as '7/1 to 7/31 between 0 and 23 @1' or '7/21 to 7/21 between 0 and 23 @1'.",
        tags={
            "run-energy",
            "weather",
            "epw",
            "uwg",
            "alternative-weather",
            "data-collection",
            "data-collection-target",
            "monthly-chart",
            "hourly-plot",
            "visualize",
            "timeseries",
            "dry-bulb-temperature",
            "relative-humidity",
            "wind-speed",
            "radiation",
            "target",
            "garden",
            "safe",
        },
        timeout=60,
    )
    def read_weather_file_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Garden weather_file target returned by download_epw, search_weather_files, run_uwg, or get_uwg_run. Provide exactly one of weather_target or epw_path."
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
                description="EPW data field or alias. Examples: dry_bulb_temperature, dry_bulb, relative_humidity, wind_speed, wind_direction, direct_normal_radiation, diffuse_horizontal_radiation, global_horizontal_radiation, dew_point_temperature, atmospheric_station_pressure."
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
            Field(description="Maximum values returned in summary when include_values is true."),
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
