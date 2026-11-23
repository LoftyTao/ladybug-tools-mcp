"""comfort MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register comfort tools."""

    @mcp.tool(
        name="LB_Calculate_Adaptive",
        description=(
            "Calculate ASHRAE-55 or EN-16798 Adaptive comfort from Garden "
            "Ladybug DataCollection targets. Required inputs are outdoor "
            "temperature and operative temperature in C; the outdoor target "
            "must be annual continuous data unless it already uses a prevailing "
            "outdoor temperature data type. Optional air speed in m/s defaults "
            "to 0.1 m/s. Returns one persisted degrees-from-neutral "
            "ladybug_data_collection target, compact statistics and comfort "
            "percentages for existing chart or export tools."
        ),
        tags={"ladybug", "comfort", "thermal-comfort", "data-collection", "adaptive"},
        timeout=60,
    )
    def calculate_adaptive(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        outdoor_temperature_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for annual outdoor temperature or prevailing outdoor temperature in C."),
        ],
        operative_temperature_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for operative temperature in C."),
        ],
        air_speed_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden ladybug_data_collection target for indoor air speed in m/s; defaults to 0.1 m/s."),
        ] = None,
        comfort_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional AdaptiveParameter dictionary; defaults to ASHRAE-55 with averaged-monthly prevailing temperature."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the persisted Adaptive result target."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return the full Adaptive DataCollection dictionary in addition to the compact target; default false."),
        ] = False,
    ) -> dict[str, Any]:
        """Calculate and persist Adaptive comfort values."""
        from garden.comfort import calculate_adaptive as service

        return service(
            garden_root=garden_root,
            outdoor_temperature_target=outdoor_temperature_target,
            operative_temperature_target=operative_temperature_target,
            air_speed_target=air_speed_target,
            comfort_parameter=comfort_parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    @mcp.tool(
        name="LB_Calculate_PMV",
        description=(
            "Calculate Predicted Mean Vote (PMV) values from Garden-backed "
            "Ladybug DataCollection targets. Required inputs are air temperature "
            "in C and relative humidity in %; optional mean radiant temperature, "
            "air speed, metabolic rate, clothing insulation and external work "
            "accept targets or scalar values and otherwise use Ladybug Comfort "
            "defaults. Returns one persisted predicted-mean-vote "
            "ladybug_data_collection target, compact PMV/PPD statistics and "
            "comfort percentages for downstream chart or export tools."
        ),
        tags={"ladybug", "comfort", "thermal-comfort", "data-collection", "pmv"},
        timeout=60,
    )
    def calculate_pmv(
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
        air_speed: Annotated[
            dict[str, Any] | float | int | None,
            Field(description="Optional air speed in m/s as a scalar or Garden DataCollection target; defaults to 0.1 m/s."),
        ] = None,
        met_rate: Annotated[
            dict[str, Any] | float | int | None,
            Field(description="Optional metabolic rate in met as a scalar or Garden DataCollection target; defaults to 1.1 met."),
        ] = None,
        clo_value: Annotated[
            dict[str, Any] | float | int | None,
            Field(description="Optional clothing insulation in clo as a scalar or Garden DataCollection target; defaults to 0.7 clo."),
        ] = None,
        external_work: Annotated[
            dict[str, Any] | float | int | None,
            Field(description="Optional external work in met as a scalar or Garden DataCollection target; defaults to 0 met."),
        ] = None,
        comfort_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional PMVParameter dictionary; defaults to PPD threshold 10 percent."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the persisted PMV result target."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return the full PMV DataCollection dictionary in addition to the compact target; default false."),
        ] = False,
    ) -> dict[str, Any]:
        """Calculate and persist PMV values."""
        from garden.comfort import calculate_pmv as service

        return service(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target,
            relative_humidity_target=relative_humidity_target,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            air_speed=air_speed,
            met_rate=met_rate,
            clo_value=clo_value,
            external_work=external_work,
            comfort_parameter=comfort_parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    @mcp.tool(
        name="LB_Calculate_UTCI",
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
