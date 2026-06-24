"""Write Dragonfly DES Modelica project MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import write_modelica_project as service


def register(mcp: FastMCP) -> None:
    """Register the Modelica project write candidate tool."""

    @mcp.tool(
        name="write_modelica_project",
        description=(
            "Candidate boundary for writing a Modelica project from DES artifact "
            "targets. It uses the system_params JSON, feature GeoJSON, and "
            "scenario CSV saved in the Garden, then returns runtime_status, "
            "run_target, modelica_project_target when written, summary_view, "
            "poll_next, and report. Numeric Modelica results are outside scope."
        ),
        tags={"dragonfly", "district-energy", "project", "artifact", "runtime", "run", "target"},
        timeout=60,
    )
    def write_modelica_project(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the candidate Modelica project is written inside this Garden.")],
        system_parameter_json_target: Annotated[dict[str, Any], Field(description="DES system_params JSON artifact target from export or sys-param sizing.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target used to build the Modelica project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target used to build the Modelica project.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Write a candidate DES Modelica project."""
        return service(
            garden_root=garden_root,
            system_parameter_json_target=system_parameter_json_target,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
        )
