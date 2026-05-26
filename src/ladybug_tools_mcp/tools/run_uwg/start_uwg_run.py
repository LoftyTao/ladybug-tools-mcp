"""Start UWG run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import start_uwg_run as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_start_simulation tool.'

    @mcp.tool(
        name="start_simulation",
        description=(
            "Start a Dragonfly UWG Alternative Weather morphing run from a Dragonfly "
            "model and Garden EPW weather target. A finished run registers a morphed "
            "urban weather_target for optional downstream Energy simulation. Returns "
            "run_target, uwg_run_target, runtime_status through summary_view.status, "
            "poll_next, and report; poll with uwg_poll_simulation before using the "
            "morphed weather. Treat a failed runtime_status as requiring report review."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "simulate",
            "start",
        },
        timeout=120,
    )
    def start_uwg_run(
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
