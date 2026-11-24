"""run_urbanopt MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register run_urbanopt tools."""

    @mcp.tool(
        name="DF_URBANopt_Prepare_Project",
        description=(
            "Prepare a Garden-managed URBANopt project folder from a Dragonfly "
            "feature GeoJSON artifact. Supports workflow_mode='energy' (Energy "
            "simulation project folder + scenario CSV target) and workflow_mode='des' "
            "(DES scenario CSV target). Missing URBANopt is reported as blocked with "
            "LB_Get_Runtime_Config as the next check."
        ),
        tags={"dragonfly", "urbanopt", "energy", "district-energy", "project", "artifact", "runtime", "target"},
        timeout=30,
    )
    def prepare_project(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json; URBANopt project setup is written inside this Garden."),
        ],
        feature_geojson_target: Annotated[
            dict[str, Any],
            Field(description="Dragonfly URBANopt/DES feature GeoJSON artifact target to prepare."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target; when provided its EPW is written into the base Honeybee OSW."),
        ] = None,
        cpu_count: Annotated[
            int | None,
            Field(description="Optional positive CPU count for the URBANopt project preparation step."),
        ] = None,
        verbose: Annotated[
            bool,
            Field(description="Ask the URBANopt project preparation step to emit verbose progress output."),
        ] = False,
        workflow_mode: Annotated[
            Literal["energy", "des"],
            Field(description="Target URBANopt workflow mode: 'energy' (default) or 'des'."),
        ] = "energy",
        sim_par_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SimulationParameter target/dict written as sim_par_json into the base OSW."),
        ] = None,
        additional_measures: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional list of OpenStudio Measure dicts or Garden folder paths."),
        ] = None,
        additional_mapper_measures: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional list of URBANopt MapperMeasure dicts or Garden folder paths."),
        ] = None,
        base_osw: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional Garden-relative .osw path or OSW dict overriding the default template."),
        ] = None,
        emissions_year: Annotated[
            int | None,
            Field(description="Optional future electricity emissions year for Cambium emissions reporting."),
        ] = None,
    ) -> dict[str, Any]:
        """Prepare an URBANopt Energy or DES project folder."""
        if workflow_mode == "des":
            from garden.dragonfly_des.runs import prepare_urbanopt_project as service
        else:
            from garden.run_urbanopt import prepare_project as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            weather_target=weather_target,
            cpu_count=cpu_count,
            verbose=verbose,
            sim_par_target=sim_par_target,
            additional_measures=additional_measures,
            additional_mapper_measures=additional_mapper_measures,
            base_osw=base_osw,
            emissions_year=emissions_year,
        )

    @mcp.tool(
        name="DF_URBANopt_Start_Simulation",
        description=(
            "Start an URBANopt Energy or DES simulation from a feature GeoJSON "
            "target and scenario CSV target (plus prepared_project_target when "
            "workflow_mode='energy'). Writes a Garden run ledger with poll_next pointing "
            "to GD_Poll_Run. Optionally pass wait_seconds to wait for completion in one "
            "call. Missing URBANopt is reported as blocked with LB_Get_Runtime_Config."
        ),
        tags={"dragonfly", "urbanopt", "energy", "district-energy", "energyplus", "run", "simulate", "runtime", "target"},
        timeout=300,
    )
    def start_simulation(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json; the URBANopt run ledger is written inside this Garden."),
        ],
        feature_geojson_target: Annotated[
            dict[str, Any],
            Field(description="Dragonfly URBANopt/DES feature GeoJSON artifact target for the simulation."),
        ],
        scenario_csv_target: Annotated[
            dict[str, Any],
            Field(description="URBANopt scenario CSV artifact target paired with the feature GeoJSON."),
        ],
        prepared_project_target: Annotated[
            dict[str, Any] | None,
            Field(description="URBANopt project folder target returned by DF_URBANopt_Prepare_Project; required when workflow_mode='energy'."),
        ] = None,
        workflow_mode: Annotated[
            Literal["energy", "des"],
            Field(description="Target URBANopt workflow mode: 'energy' (default) or 'des'."),
        ] = "energy",
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run id; omit to let the Garden create one."),
        ] = None,
        cpu_count: Annotated[
            int | None,
            Field(description="Optional CPU count passed to the Dragonfly Energy URBANopt runner."),
        ] = None,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional seconds to poll for completion before returning; omit to return immediately."),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is provided."),
        ] = 2.0,
    ) -> dict[str, Any]:
        """Start an URBANopt Energy or DES simulation."""
        if workflow_mode == "des":
            from garden.dragonfly_des.runs import start_urbanopt_simulation as service

            return service(
                garden_root=garden_root,
                feature_geojson_target=feature_geojson_target,
                scenario_csv_target=scenario_csv_target,
                run_id=run_id,
                cpu_count=cpu_count,
                wait_seconds=wait_seconds,
                poll_interval=poll_interval,
            )

        if prepared_project_target is None:
            raise ValueError(
                "prepared_project_target is required when workflow_mode='energy'."
            )
        from garden.run_urbanopt import start_simulation as service

        return service(
            garden_root=garden_root,
            prepared_project_target=prepared_project_target,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            cpu_count=cpu_count,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
        )

    @mcp.tool(
        name="DF_URBANopt_Read_Results",
        description=(
            "Generate (via run_default_report) and read URBANopt default scenario reports "
            "(default_scenario_report.json/.csv) plus per-building EnergyPlus SQL summaries "
            "(EUI, end uses, peak electric demand, and optional emissions)."
        ),
        tags={"dragonfly", "urbanopt", "energy", "result", "eui", "sql", "target"},
        timeout=120,
    )
    def read_urbanopt_results(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        feature_geojson_target: Annotated[
            dict[str, Any],
            Field(description="Dragonfly URBANopt/DES feature GeoJSON artifact target."),
        ],
        scenario_csv_target: Annotated[
            dict[str, Any],
            Field(description="URBANopt scenario CSV artifact target."),
        ],
        run_default_report: Annotated[
            bool,
            Field(description="Invoke URBANopt default report generation when runtime is available."),
        ] = True,
        include_building_sql_summary: Annotated[
            bool,
            Field(description="Extract per-building EnergyPlus SQL EUI, end-use, and peak summaries."),
        ] = True,
        subregion: Annotated[
            str | None,
            Field(description="Optional eGRID/Cambium subregion code for per-building SQL emissions."),
        ] = None,
    ) -> dict[str, Any]:
        """Read URBANopt default scenario reports and per-building SQL summaries."""
        from garden.run_urbanopt import read_urbanopt_results as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_default_report=run_default_report,
            include_building_sql_summary=include_building_sql_summary,
            subregion=subregion,
        )
