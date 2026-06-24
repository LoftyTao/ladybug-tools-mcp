"""Start Dragonfly DES system-parameter run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import start_sys_param as service


def register(mcp: FastMCP) -> None:
    """Register the DES system-parameter start tool."""

    @mcp.tool(
        name="start_sys_param",
        description=(
            "Start the DES system-parameter sizing/update step after URBANopt "
            "outputs and building loads are ready. The tool records a Garden "
            "run ledger and returns run_target, runtime_status, poll_next, "
            "summary_view, and a system_parameter_json_target handoff when one "
            "is available. Missing GMT/uo_des is returned as blocked."
        ),
        tags={"dragonfly", "district-energy", "run", "runtime", "poll", "sizing", "target"},
        timeout=30,
    )
    def start_sys_param(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the sys-param run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target for the system-parameter step.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target for the system-parameter step.")],
        system_parameter_json_target: Annotated[dict[str, Any] | None, Field(description="Existing system_params JSON artifact target to carry through the ledger, when already exported.") ] = None,
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Start a DES system-parameter run."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            run_id=run_id,
        )
