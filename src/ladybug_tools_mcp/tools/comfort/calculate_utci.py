"""Ladybug UTCI calculation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_calculate_utci tool."""

    @mcp.tool(
        name="LB_calculate_utci",
        description=(
            "Calculate Universal Thermal Climate Index (UTCI) values from "
            "Garden-backed Ladybug DataCollection targets. Required inputs are "
            "air temperature in C and relative humidity in %; optional mean "
            "radiant temperature in C and wind speed in m/s targets default to "
            "air temperature and 0.5 m/s. Returns one persisted "
            "ladybug_data_collection target, compact statistics and comfort "
            "percentages for downstream chart or JSON/CSV export. It does not "
            "return unbounded values unless return_data_collection is true."
        ),
        tags={"ladybug", "comfort", "thermal-comfort", "data-collection", "utci"},
        timeout=60,
    )
    def calculate_utci(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        air_temperature_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for air temperature in C."),
        ],
        relative_humidity_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for relative humidity in percent."),
        ],
        mean_radiant_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for mean radiant temperature in C; defaults to air temperature."),
        ] = None,
        wind_speed_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for meteorological wind speed in m/s; defaults to 0.5 m/s."),
        ] = None,
        comfort_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional UTCIParameter dictionary; defaults to UTCI thresholds of 9 C cold and 26 C heat."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the persisted UTCI result target."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return the full UTCI DataCollection dictionary in addition to the compact target; default false."),
        ] = False,
    ) -> dict[str, Any]:
        """Calculate and persist UTCI values."""
        from garden.comfort import calculate_utci as service

        return service(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target,
            relative_humidity_target=relative_humidity_target,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            wind_speed_target=wind_speed_target,
            comfort_parameter=comfort_parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
