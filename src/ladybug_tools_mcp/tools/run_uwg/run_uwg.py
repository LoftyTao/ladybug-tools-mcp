"""Run UWG synchronously MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import run_uwg as service


def register(mcp: FastMCP) -> None:
    """Register the run_uwg tool."""

    @mcp.tool(
        name="run_uwg",
        description=(
            "Blocking Dragonfly Urban Weather Generator Alternative Weather "
            "weather-morphing run. It turns a rural or airport EPW into an "
            "urban EPW, records a uwg_run ledger, and registers the morphed "
            "EPW as a Garden weather_file target. Agents should prefer "
            "start_uwg_run unless the user explicitly asks to wait."
        ),
        tags={
            "run-uwg",
            "uwg",
            "alternative-weather",
            "weather-morphing",
            "dragonfly",
            "write",
            "safe",
        },
        timeout=3600,
    )
    def run_uwg(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden weather_file target with epw_path to morph."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Garden-relative EPW path fallback for controlled tests."),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target."),
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
            Field(description="Return a completed existing UWG run with the same run_id when available."),
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
            epw_path=epw_path,
            simulation_parameter_target=simulation_parameter_target,
            simulation_parameter=simulation_parameter,
            run_id=run_id,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )
