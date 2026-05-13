"""Apply Dragonfly UWG properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.uwg_properties import apply_dragonfly_uwg_properties as service


def register(mcp: FastMCP) -> None:
    """Register the apply_dragonfly_uwg_properties tool."""

    @mcp.tool(
        name="apply_dragonfly_uwg_properties",
        description=(
            "Apply SDK-backed Dragonfly UWG properties to a Dragonfly model, "
            "Building, or ContextShade target. Model fields include terrain, "
            "traffic, tree cover, and grass cover. Building fields include "
            "program, vintage, heat-to-canyon fraction, SHGC, wall/roof albedo, "
            "and roof vegetation fraction. ContextShade supports is_vegetation. "
            "These UWG properties are separate from Dragonfly Energy/OpenStudio "
            "properties."
        ),
        tags={
            "run-uwg",
            "uwg",
            "alternative-weather",
            "dragonfly",
            "properties",
            "edit",
            "write",
            "safe",
        },
        timeout=20,
    )
    def apply_dragonfly_uwg_properties(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Dragonfly model, Building, or ContextShade target."),
        ] = None,
        target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for host_target."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        terrain: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg Terrain dictionary for model-level UWG ground properties."),
        ] = None,
        traffic: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg TrafficParameter dictionary for model-level anthropogenic traffic heat."),
        ] = None,
        tree_coverage_fraction: Annotated[
            float | None,
            Field(description="Optional model-level tree coverage fraction from 0 to 1."),
        ] = None,
        grass_coverage_fraction: Annotated[
            float | None,
            Field(description="Optional model-level grass/shrub coverage fraction from 0 to 1."),
        ] = None,
        program: Annotated[
            str | None,
            Field(description="Optional UWG building program, such as LargeOffice or MidriseApartment."),
        ] = None,
        vintage: Annotated[
            str | None,
            Field(description="Optional UWG building vintage, such as New, 1980_Present, or Pre1980."),
        ] = None,
        fract_heat_to_canyon: Annotated[
            float | None,
            Field(description="Optional fraction of waste heat rejected to the urban canyon."),
        ] = None,
        shgc: Annotated[
            float | None,
            Field(description="Optional average window solar heat gain coefficient."),
        ] = None,
        wall_albedo: Annotated[
            float | None,
            Field(description="Optional wall albedo for UWG building surfaces."),
        ] = None,
        roof_albedo: Annotated[
            float | None,
            Field(description="Optional roof albedo for UWG building surfaces."),
        ] = None,
        roof_veg_fraction: Annotated[
            float | None,
            Field(description="Optional fraction of roof covered by vegetation."),
        ] = None,
        is_vegetation: Annotated[
            bool | None,
            Field(description="Optional ContextShade flag used to mark vegetation for UWG tree coverage."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Dragonfly UWG properties."""
        if host_target is None:
            host_target = target
        if host_target is None:
            raise ValueError("apply_dragonfly_uwg_properties requires host_target or target.")
        return service(
            garden_root=garden_root,
            host_target=host_target,
            model_target=model_target,
            terrain=terrain,
            traffic=traffic,
            tree_coverage_fraction=tree_coverage_fraction,
            grass_coverage_fraction=grass_coverage_fraction,
            program=program,
            vintage=vintage,
            fract_heat_to_canyon=fract_heat_to_canyon,
            shgc=shgc,
            wall_albedo=wall_albedo,
            roof_albedo=roof_albedo,
            roof_veg_fraction=roof_veg_fraction,
            is_vegetation=is_vegetation,
        )
