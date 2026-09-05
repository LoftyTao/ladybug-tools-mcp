"""Ladybug Adaptive comfort calculation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_calculate_adaptive tool."""

    @mcp.tool(
        name="LB_calculate_adaptive",
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
