"""Start UWG run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import start_uwg_run as service


def register(mcp: FastMCP) -> None:
    """Register the start_uwg_run tool."""

    @mcp.tool(
        name="start_uwg_run",
        description=(
            "Start a UWG Alternative Weather weather-morphing run and poll "
            "get_uwg_run. Use a Dragonfly model plus an exact Garden "
            "weather_file target. The completed run returns a morphed urban "
            "weather_target that can be passed to "
            "start_energy_run only when downstream Energy simulation is "
            "requested."
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
        timeout=120,
    )
    def start_uwg_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden weather_file target with epw_path to morph."),
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
            Field(description="Validate the EPW with Ladybug before scheduling UWG."),
        ] = True,
    ) -> dict[str, Any]:
        """Start UWG in the background."""
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
