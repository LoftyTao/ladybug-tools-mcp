"""run_uwg MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register run_uwg tools."""

    @mcp.tool(
        name="DF_UWG_Properties",
        description=(
            "Inspect or apply Dragonfly Urban Weather Generator (UWG) extension "
            "properties on a Dragonfly model, Building, or ContextShade target. "
            "Use action='get_summary' to read UWG settings, or action='apply' with "
            "host_target to update model terrain/traffic/vegetation coverage, Building "
            "program/vintage/albedo/SHGC/heat-to-canyon, or ContextShade is_vegetation."
        ),
        tags={"dragonfly", "uwg", "weather", "edit", "summary", "urban-weather"},
        timeout=20,
    )
    def uwg_properties(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        action: Annotated[
            Literal["get_summary", "apply", "create_helper"],
            Field(description="Action to run: 'get_summary', 'apply', or 'create_helper'."),
        ] = "get_summary",
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Dragonfly model, Building, or ContextShade target (required when action='apply')."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to base Dragonfly model."),
        ] = None,
        climate_zone: Annotated[
            str | None,
            Field(description="Optional ASHRAE climate zone for computing average_shgc in action='get_summary'."),
        ] = None,
        helper_type: Annotated[
            Literal[
                "terrain",
                "traffic_parameter",
                "vegetation_parameter",
                "reference_epw_site",
                "boundary_layer_parameter",
            ]
            | None,
            Field(description="Typed UWG helper to construct when action='create_helper'."),
        ] = None,
        helper_params: Annotated[
            dict[str, Any] | None,
            Field(description="Parameters dict for action='create_helper'."),
        ] = None,
        terrain: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg Terrain dictionary for model-level UWG ground properties."),
        ] = None,
        traffic: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg TrafficParameter dictionary for model-level traffic heat."),
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
            Field(description="Optional UWG building program."),
        ] = None,
        vintage: Annotated[
            Literal["New", "1980_Present", "Pre1980"] | None,
            Field(description="Optional UWG building vintage: New, 1980_Present, or Pre1980."),
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
        infer_program_from_energy_program: Annotated[
            bool,
            Field(description="Infer Building UWG program from its Dragonfly Energy ProgramType when action='apply'."),
        ] = False,
    ) -> dict[str, Any]:
        """Inspect, construct helpers for, or apply Dragonfly UWG properties."""
        if action == "get_summary":
            from garden.dragonfly_core.uwg_properties import (
                get_dragonfly_uwg_properties_summary as service,
            )

            return service(
                garden_root=garden_root,
                model_target=model_target,
                climate_zone=climate_zone,
            )

        if action == "create_helper":
            if not helper_type:
                raise ValueError("DF_UWG_Properties with action='create_helper' requires helper_type.")
            from garden.dragonfly_core.uwg_properties import create_uwg_helper as service

            return service(
                helper_type=helper_type,
                params=helper_params,
                garden_root=garden_root,
                model_target=model_target,
            )

        if host_target is None:
            raise ValueError("DF_UWG_Properties with action='apply' requires host_target.")
        from garden.dragonfly_core.uwg_properties import apply_dragonfly_uwg_properties as service

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
            infer_program_from_energy_program=infer_program_from_energy_program,
        )

    @mcp.tool(
        name="DF_UWG_Run",
        description=(
            "Create UWG simulation parameters, export UWG JSON, or run UWG weather "
            "morphing in a Garden. mode='create_parameter' creates a UWGSimulationParameter; "
            "mode='export_json' writes a UWG JSON artifact; mode='simulate' starts a "
            "background UWG worker (with poll_next pointing to GD_Poll_Run, and optional "
            "wait_seconds to wait for completion in one call)."
        ),
        tags={"dragonfly", "uwg", "weather", "author", "export", "simulate", "urban-weather"},
        timeout=3600,
    )
    def run_uwg_workflow(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        mode: Annotated[
            Literal["create_parameter", "export_json", "simulate"],
            Field(description="UWG workflow mode: 'create_parameter', 'export_json', or 'simulate'."),
        ] = "simulate",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden weather_file target returned by LB_Manage_Weather."),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target."),
        ] = None,
        simulation_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline UWGSimulationParameter dictionary."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier when mode='create_parameter'."),
        ] = None,
        climate_zone: Annotated[
            str | None,
            Field(description="Optional UWG ASHRAE climate zone such as 5A when mode='create_parameter'."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dict with start_month, start_day, end_month, and end_day (mode='create_parameter')."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="UWG timesteps per hour when mode='create_parameter'. Default is 12."),
        ] = 12,
        vegetation_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg VegetationParameter dictionary (mode='create_parameter')."),
        ] = None,
        reference_epw_site: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg ReferenceEPWSite dictionary (mode='create_parameter')."),
        ] = None,
        boundary_layer_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg BoundaryLayerParameter dictionary (mode='create_parameter')."),
        ] = None,
        save: Annotated[
            bool,
            Field(description="Save the parameter JSON into Garden artifacts/uwg/parameters (mode='create_parameter')."),
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional artifact name when mode='export_json'."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full parameter or UWG JSON body for create_parameter / export_json."),
        ] = False,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier when mode='simulate'."),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(description="Return an existing completed UWG run with the same run_id when available."),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run UWG silently when supported by the SDK."),
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(description="Validate the EPW with Ladybug before running UWG."),
        ] = True,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional seconds to poll for completion when mode='simulate'; omit to return immediately."),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is provided."),
        ] = 2.0,
    ) -> dict[str, Any]:
        """Create UWG parameters, export UWG JSON, or run UWG simulation."""
        if mode == "create_parameter":
            from garden.run_uwg import create_uwg_simulation_parameter as service

            return service(
                garden_root=garden_root,
                identifier=identifier,
                climate_zone=climate_zone,
                run_period=run_period,
                timestep=timestep,
                vegetation_parameter=vegetation_parameter,
                reference_epw_site=reference_epw_site,
                boundary_layer_parameter=boundary_layer_parameter,
                save=save,
                include_body=include_body,
            )
        if mode == "export_json":
            from garden.run_uwg import dragonfly_model_to_uwg as service

            return service(
                garden_root=garden_root,
                model_target=model_target,
                weather_target=weather_target,
                simulation_parameter_target=simulation_parameter_target,
                simulation_parameter=simulation_parameter,
                name=name,
                include_body=include_body,
            )
        from garden.run_uwg import start_uwg_run as service

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
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
        )
