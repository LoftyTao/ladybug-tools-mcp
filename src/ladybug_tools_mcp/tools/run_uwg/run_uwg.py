"""Run UWG synchronously MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import run_uwg as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_run_simulation_wait tool.'

    @mcp.tool(
        name="run_simulation_wait",
        description=(
            "Run a blocking Dragonfly Urban Weather Generator Alternative Weather "
            "morphing workflow from a rural or airport EPW to an urban EPW. It records "
            "a uwg_run ledger and registers the morphed EPW as a Garden weather_file "
            "target. Returns run_target, uwg_run_target, runtime_status through "
            "summary_view.status, and report. Treat a failed runtime_status as requiring "
            "report review. Prefer uwg_start_simulation unless the user asks to wait."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "simulate",
            "blocking",
        },
        timeout=3600,
    )
    def run_uwg(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden weather file target returned by energyplus_download_epw or a Garden-relative EPW path to morph with UWG.'),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target returned by uwg_create_simulation_parameter."),
        ] = None,
        simulation_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline UWGSimulationParameter dictionary."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(description="Return an existing finished UWG run with the same run_id when available."),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run UWG silently when supported by the SDK."),
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(description="Validate the EPW with Ladybug before running UWG."),
        ] = True,
    ) -> dict[str, Any]:
        """Run UWG synchronously."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            simulation_parameter=simulation_parameter,
            run_id=run_id,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )
