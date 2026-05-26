"""Dragonfly model to UWG JSON MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.writer import dragonfly_model_to_uwg as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_dragonfly_model_to_uwg tool.'

    @mcp.tool(
        name='dragonfly_model_to_uwg',
        description=(
            "Write a UWG JSON artifact from a Dragonfly model, rural/airport "
            "Garden EPW weather target, and optional UWG simulation parameter. "
            "Use this to inspect or archive UWG inputs without running the UWG. "
            "This is an Alternative Weather input export, not a URBANopt Scenario."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "export",
            "urban-weather",
        },
        timeout=60,
    )
    def dragonfly_model_to_uwg(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
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
        name: Annotated[
            str | None,
            Field(description="Optional artifact name. Defaults to <model>_uwg."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full UWG JSON body. Keep False for compact target handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Write a UWG JSON artifact."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            simulation_parameter=simulation_parameter,
            name=name,
            include_body=include_body,
        )
