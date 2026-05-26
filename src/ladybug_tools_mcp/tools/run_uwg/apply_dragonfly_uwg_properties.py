"""Apply Dragonfly UWG properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.uwg_properties import apply_dragonfly_uwg_properties as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_apply_dragonfly_properties tool.'

    @mcp.tool(
        name='apply_dragonfly_properties',
        description=(
            "Apply SDK-backed Dragonfly UWG properties to a Dragonfly model, "
            "Building, or ContextShade target. Requires host_target; "
            "use the Dragonfly model target for model-level tree_coverage_fraction "
            "and grass_coverage_fraction, and use Building targets for program, "
            "vintage, heat-to-canyon fraction, SHGC, wall/roof albedo, and roof "
            "vegetation fraction. Omit terrain in simple workflows unless you "
            "already have a Dragonfly UWG Terrain dictionary; terrain is not a "
            "string such as Suburban. Building program values include LargeOffice, "
            "MediumOffice, SmallOffice, and MidriseApartment; not Office. Vintage "
            "values are New, 1980_Present, or Pre1980; not ASHRAE_2019. "
            "ContextShade supports is_vegetation. "
            "These UWG properties are separate from Dragonfly Energy/OpenStudio "
            "properties and do not launch weather morphing."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "edit",
            "urban-weather",
        },
        timeout=20,
    )
    def apply_dragonfly_uwg_properties(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Dragonfly model target, Building target, or ContextShade target. "
                    "This tool requires host_target."
                ),
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
        terrain: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional dragonfly_uwg Terrain dictionary for model-level UWG "
                    "ground properties. Omit terrain unless you already have a real "
                    "Terrain object dictionary; it is not a string like Suburban."
                ),
            ),
        ] = None,
        traffic: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg TrafficParameter dictionary for model-level anthropogenic traffic heat in UWG weather morphing."),
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
            Literal[
                "LargeOffice",
                "MediumOffice",
                "SmallOffice",
                "MidriseApartment",
                "Retail",
                "StripMall",
                "PrimarySchool",
                "SecondarySchool",
                "SmallHotel",
                "LargeHotel",
                "Hospital",
                "Outpatient",
                "Warehouse",
                "SuperMarket",
                "FullServiceRestaurant",
                "QuickServiceRestaurant",
            ]
            | None,
            Field(
                description=(
                    "Optional UWG building program. Valid examples: LargeOffice, "
                    "MediumOffice, SmallOffice, MidriseApartment, Retail, StripMall, "
                    "PrimarySchool, SecondarySchool, SmallHotel, LargeHotel, Hospital, "
                    "Outpatient, Warehouse, SuperMarket, FullServiceRestaurant, "
                    "QuickServiceRestaurant. Not Office."
                ),
            ),
        ] = None,
        vintage: Annotated[
            Literal["New", "1980_Present", "Pre1980"] | None,
            Field(
                description=(
                    "Optional UWG building vintage. Valid values are New, "
                    "1980_Present, or Pre1980. Not ASHRAE_2019."
                ),
            ),
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
