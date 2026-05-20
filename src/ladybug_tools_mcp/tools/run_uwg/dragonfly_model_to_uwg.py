"""Dragonfly model to UWG JSON MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.writer import dragonfly_model_to_uwg as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_model_to_uwg tool."""

    @mcp.tool(
        name="dragonfly_model_to_uwg",
        description=(
            "Write a UWG JSON artifact from a Dragonfly model, rural/airport "
            "Garden EPW weather target, and optional UWG simulation parameter. "
            "Use this to inspect or archive UWG inputs without running the UWG."
        ),
        tags={
            "run-uwg",
            "uwg",
            "alternative-weather",
            "dragonfly",
            "epw",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def dragonfly_model_to_uwg(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
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
        name: Annotated[
            str | None,
            Field(description="Optional artifact name. Defaults to <model>_uwg."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full UWG JSON body. Keep False for Agent workflows."),
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
