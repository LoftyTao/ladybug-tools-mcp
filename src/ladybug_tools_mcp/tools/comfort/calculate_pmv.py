"""Ladybug PMV comfort calculation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_calculate_pmv tool."""

    @mcp.tool(
        name="LB_calculate_pmv",
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
