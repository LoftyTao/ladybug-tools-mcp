"""Start Dragonfly DES URBANopt simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import start_urbanopt_simulation as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt start tool."""

    @mcp.tool(
        name="start_urbanopt_simulation",
        description=(
            "Start the URBANopt simulation step for DES artifacts already saved "
            "in a Garden. The tool writes a Garden run ledger and returns "
            "run_target, runtime_status, poll_next, summary_view, and report "
            "without waiting for result parsing. Missing URBANopt is reported as "
            "blocked, with config_get_runtime_config named as the next check."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "run", "simulate", "runtime", "poll", "target"},
        timeout=30,
    )
    def start_urbanopt_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target for the URBANopt simulation.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
        cpu_count: Annotated[int | None, Field(description="Optional CPU count passed to the Dragonfly Energy URBANopt runner.") ] = None,
    ) -> dict[str, Any]:
        """Start an URBANopt simulation."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            cpu_count=cpu_count,
        )
