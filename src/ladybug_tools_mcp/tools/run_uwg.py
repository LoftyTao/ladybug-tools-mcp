"""run_uwg MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register run_uwg tools."""

    @mcp.tool(
        name="DF_UWG_Apply_Dragonfly_Properties",
        description=(
            'Apply SDK-backed Dragonfly UWG properties to a Dragonfly model, Building, or '
            'ContextShade target. Requires host_target; use the Dragonfly model target for '
            'model-level tree_coverage_fraction and grass_coverage_fraction, and use Building '
            'targets for program, vintage, heat-to-canyon fraction, SHGC, wall/roof albedo, and '
            'roof vegetation fraction. Terrain accepts a Dragonfly UWG Terrain dictionary. '
            'Building program values include LargeOffice, MediumOffice, SmallOffice, and '
            'MidriseApartment; vintage values are New, 1980_Present, or Pre1980. ContextShade '
            'supports is_vegetation.'
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
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
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
                    'Optional dragonfly_uwg Terrain dictionary for model-level UWG ground properties.'
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
                    'Optional UWG building program. Valid examples: LargeOffice, MediumOffice, '
                    'SmallOffice, MidriseApartment, Retail, StripMall, PrimarySchool, '
                    'SecondarySchool, SmallHotel, LargeHotel, Hospital, Outpatient, Warehouse, '
                    'SuperMarket, FullServiceRestaurant, QuickServiceRestaurant.'
                ),
            ),
        ] = None,
        vintage: Annotated[
            Literal["New", "1980_Present", "Pre1980"] | None,
            Field(
                description=(
                    'Optional UWG building vintage. Valid values are New, 1980_Present, or Pre1980.'
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
        )

    @mcp.tool(
        name="DF_UWG_Create_Simulation_Parameter",
        description=(
            'Create and optionally save a Dragonfly UWGSimulationParameter for Alternative '
            'Weather workflows. Use this before DF_UWG_Dragonfly_Model_To_UWG, '
            'DF_UWG_Start_Simulation, or DF_UWG_Run_Simulation_Wait when custom run period, '
            'timestep, vegetation, reference EPW site, or boundary layer settings are needed. '
            'Returns target, summary_view, persistence_receipt, and report when saved.'
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "author",
            "parameter",
        },
        timeout=20,
    )
    def create_uwg_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the saved UWGSimulationParameter JSON target."),
        ] = None,
        climate_zone: Annotated[
            str | None,
            Field(description="Optional UWG ASHRAE climate zone such as 5A. Defaults to SDK autocalculate."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dict with start_month, start_day, end_month, and end_day."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="UWG timesteps per hour. Default is 12."),
        ] = 12,
        vegetation_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg VegetationParameter dictionary."),
        ] = None,
        reference_epw_site: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg ReferenceEPWSite dictionary."),
        ] = None,
        boundary_layer_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dragonfly_uwg BoundaryLayerParameter dictionary."),
        ] = None,
        save: Annotated[
            bool,
            Field(description="Save the parameter JSON into Garden artifacts/uwg/parameters."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Return the full UWGSimulationParameter dict. Keep False for compact target handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a UWG simulation parameter."""
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

    @mcp.tool(
        name="DF_UWG_Dragonfly_Model_To_UWG",
        description=(
            'Write a UWG JSON artifact from a Dragonfly model, rural/airport Garden EPW weather '
            'target, and optional UWG simulation parameter. Use this to inspect or archive UWG '
            'inputs without running the UWG.'
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
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden weather file target returned by EP_Import_Local_Weather or EP_Search_Weather_Files, or a Garden-relative EPW path to morph with UWG.'),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target returned by DF_UWG_Create_Simulation_Parameter."),
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

    @mcp.tool(
        name="DF_UWG_Get_Dragonfly_Properties_Summary",
        description=(
            'Read compact Dragonfly Urban Weather Generator extension properties for the model, '
            'Buildings, and ContextShades. Use this to inspect UWG setup before weather morphing. '
            'Returns summary_view and report without changing the model.'
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "summary",
            "inventory",
        },
        timeout=20,
    )
    def get_dragonfly_uwg_properties_summary(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Dragonfly UWG properties."""
        from garden.dragonfly_core.uwg_properties import (
            get_dragonfly_uwg_properties_summary as service,
        )

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="DF_UWG_Poll_Simulation",
        description=(
            "Read one Garden UWG Alternative Weather run ledger record by uwg_run target "
            "or run_id. Use after DF_UWG_Start_Simulation to poll runtime_status and locate "
            "morphed weather outputs. Returns run_target, runtime_status through "
            "summary_view.status, poll_next, and report. Treat a failed runtime_status "
            "as requiring report review before using any weather target."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "poll",
            "ledger",
        },
        timeout=20,
    )
    def get_uwg_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='UWG run target returned by DF_UWG_Start_Simulation; pass run_target for polling when available.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional UWG run id when run_target is not passed."),
        ] = None,
    ) -> dict[str, Any]:
        """Read a UWG run."""
        from garden.run_uwg import get_uwg_run as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_UWG_List_Run_Outputs",
        description=(
            "List compact output records for one UWG Alternative Weather run. Use this "
            "after DF_UWG_Poll_Simulation reports a finished runtime_status to find the "
            "morphed EPW weather target for downstream Energy simulation. Returns "
            "matches, summary_view, and report."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "result",
            "outputs",
        },
        timeout=20,
    )
    def list_uwg_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='UWG run target returned by DF_UWG_Start_Simulation; poll the run before listing morphed weather outputs.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional UWG run id when run_target is not passed."),
        ] = None,
    ) -> dict[str, Any]:
        """List UWG run outputs."""
        from garden.run_uwg import list_uwg_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_UWG_List_Runs",
        description=(
            'List UWG Alternative Weather runs recorded in a Garden ledger. Use this to find '
            'run_id or run_target before polling or reading outputs. Returns matches, '
            'summary_view, and report.'
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "poll",
            "ledger",
        },
        timeout=20,
    )
    def list_uwg_runs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status filter for Garden UWG run ledger records, such as running, completed, failed, or cancelled."),
        ] = None,
    ) -> dict:
        """List UWG runs."""
        from garden.run_uwg import list_uwg_runs as service

        return service(garden_root=garden_root, status=status)

    @mcp.tool(
        name="DF_UWG_Run_Simulation_Wait",
        description=(
            "Run a blocking Dragonfly Urban Weather Generator Alternative Weather "
            "morphing workflow from a rural or airport EPW to an urban EPW. It records "
            "a uwg_run ledger and registers the morphed EPW as a Garden weather_file "
            "target. Returns run_target, uwg_run_target, runtime_status through "
            "summary_view.status, and report. Treat a failed runtime_status as requiring "
            "report review. Prefer DF_UWG_Start_Simulation unless the user asks to wait."
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
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden weather file target returned by EP_Import_Local_Weather or EP_Search_Weather_Files, or a Garden-relative EPW path to morph with UWG.'),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target returned by DF_UWG_Create_Simulation_Parameter."),
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
        from garden.run_uwg import run_uwg as service

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

    @mcp.tool(
        name="DF_UWG_Start_Simulation",
        description=(
            "Start a Dragonfly UWG Alternative Weather morphing run from a Dragonfly "
            "model and Garden EPW weather target. A finished run registers a morphed "
            "urban weather_target for optional downstream Energy simulation. Returns "
            "run_target, uwg_run_target, runtime_status through summary_view.status, "
            "poll_next, and report; poll with DF_UWG_Poll_Simulation before using the "
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
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden weather file target returned by EP_Import_Local_Weather or EP_Search_Weather_Files, or a Garden-relative EPW path to morph with UWG.'),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional uwg_simulation_parameter target returned by DF_UWG_Create_Simulation_Parameter."),
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
        )
