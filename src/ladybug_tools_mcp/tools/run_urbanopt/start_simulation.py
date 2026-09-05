"""Start URBANopt Energy simulation MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the URBANopt Energy start tool."""

    @mcp.tool(
        name="DF_urbanopt_start_simulation",
        description=(
            "Start an URBANopt Energy simulation from a prepared Garden project, "
            "feature GeoJSON target, and scenario CSV target. The tool writes an "
            "urbanopt_run ledger and returns run_target, runtime_status, "
            "poll_next, summary_view, and report without parsing building energy "
            "results. Missing URBANopt is reported as blocked with "
            "LB_get_runtime_config as the next check."
        ),
        tags={"dragonfly", "urbanopt", "energy", "energyplus", "run", "simulate", "runtime", "poll", "target"},
        timeout=30,
    )
    def start_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is written inside this Garden.")],
        prepared_project_target: Annotated[dict[str, Any], Field(description="URBANopt project folder target returned by urbanopt_prepare_project.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Dragonfly URBANopt feature GeoJSON artifact target for the simulation.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="URBANopt scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
        cpu_count: Annotated[int | None, Field(description="Optional CPU count passed to the Dragonfly Energy URBANopt runner.") ] = None,
    ) -> dict[str, Any]:
        """Start an URBANopt Energy simulation."""
        from garden.run_urbanopt.run import start_simulation as service

        return service(
            garden_root=garden_root,
            prepared_project_target=prepared_project_target,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            cpu_count=cpu_count,
        )
