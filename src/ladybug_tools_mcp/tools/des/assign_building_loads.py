"""Assign Dragonfly DES building loads MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DES load assignment tool."""

    @mcp.tool(
        name="DF_des_assign_building_loads",
        description=(
            "Attach URBANopt building load results to the DES feature GeoJSON "
            "and scenario CSV artifacts before system-parameter sizing. The "
            "response reports runtime_status, summary_view, and any warnings "
            "from the Dragonfly Energy load handoff, including sensible-load "
            "substitution when district load columns are missing."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "load", "csv", "runtime", "target"},
        timeout=60,
    )
    def assign_building_loads(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; updated DES artifacts remain inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target receiving the building load references.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target paired with the feature GeoJSON.")],
    ) -> dict[str, Any]:
        """Assign building loads for DES."""
        from garden.dragonfly_des.runs import assign_building_loads as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
        )
