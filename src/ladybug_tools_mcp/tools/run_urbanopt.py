"""run_urbanopt MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register run_urbanopt tools."""

    @mcp.tool(
        name="DF_URBANopt_List_Run_Outputs",
        description=(
            "List discovered output files for an URBANopt Energy simulation run. "
            "Use this after urbanopt_poll_simulation to find SQL, ERR, HTML, "
            "CSV, OSM, IDF, log, and other URBANopt/EnergyPlus artifacts before "
            "calling downstream diagnostics or DES load tools. Returns "
            "run_target, runtime_status, matches, summary_view, and report."
        ),
        tags={"dragonfly", "urbanopt", "energy", "energyplus", "outputs", "run", "artifact", "target"},
        timeout=10,
    )
    def list_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; output paths are returned relative to this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description='Optional urbanopt_run target returned by DF_URBANopt_Start_Simulation.') ] = None,
        run_id: Annotated[str | None, Field(description="Optional URBANopt run id when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """List URBANopt Energy run outputs."""
        from garden.run_urbanopt import list_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_URBANopt_Poll_Simulation",
        description=(
            "Read the compact Garden ledger for an URBANopt Energy simulation. Use this after "
            "DF_URBANopt_Start_Simulation to inspect run_target, runtime_status, poll_next, "
            "summary_view, and report."
        ),
        tags={"dragonfly", "urbanopt", "energy", "run", "runtime", "poll", "target"},
        timeout=10,
    )
    def poll_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description='Optional urbanopt_run target returned by DF_URBANopt_Start_Simulation.') ] = None,
        run_id: Annotated[str | None, Field(description="Optional URBANopt run id when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll an URBANopt Energy simulation."""
        from garden.run_urbanopt import poll_simulation as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_URBANopt_Prepare_Project",
        description=(
            "Prepare a Garden-managed URBANopt Energy project from a Dragonfly "
            "URBANopt feature GeoJSON artifact. The tool records a project "
            "folder target and scenario CSV target, then returns runtime_status, "
            "summary_view, persistence_receipt, and report. Missing URBANopt is "
            "reported as blocked with LB_Get_Runtime_Config as the next check."
        ),
        tags={"dragonfly", "urbanopt", "energy", "project", "artifact", "runtime", "target"},
        timeout=30,
    )
    def prepare_project(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; URBANopt project setup is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Dragonfly URBANopt feature GeoJSON artifact target to prepare for URBANopt Energy simulation.")],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target; when provided its EPW is written into the base Honeybee OSW before URBANopt simulation."),
        ] = None,
        cpu_count: Annotated[int | None, Field(description="Optional positive CPU count for the URBANopt project preparation step.") ] = None,
        verbose: Annotated[bool, Field(description="Ask the URBANopt project preparation step to emit verbose progress output.") ] = False,
    ) -> dict[str, Any]:
        """Prepare an URBANopt Energy project folder."""
        from garden.run_urbanopt import prepare_project as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            weather_target=weather_target,
            cpu_count=cpu_count,
            verbose=verbose,
        )

    @mcp.tool(
        name="DF_URBANopt_Start_Simulation",
        description=(
            "Start an URBANopt Energy simulation from a prepared Garden project, "
            "feature GeoJSON target, and scenario CSV target. The tool writes an "
            "urbanopt_run ledger and returns run_target, runtime_status, "
            "poll_next, summary_view, and report without parsing building energy "
            "results. Missing URBANopt is reported as blocked with "
            "LB_Get_Runtime_Config as the next check."
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
        from garden.run_urbanopt import start_simulation as service

        return service(
            garden_root=garden_root,
            prepared_project_target=prepared_project_target,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            cpu_count=cpu_count,
        )
