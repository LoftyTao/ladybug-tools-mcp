"""des MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


DesObjectKind = Literal[
    "thermal_connector",
    "horizontal_pipe_parameter",
    "ghe_soil_parameter",
    "ghe_fluid_parameter",
    "ghe_pipe_parameter",
    "ghe_borehole_parameter",
    "ghe_design_parameter",
    "ground_heat_exchanger",
    "heating_plant",
    "cooling_plant",
    "heat_exchanger_ets",
    "heat_pump_ets",
    "fourth_gen_thermal_loop",
    "fifth_gen_thermal_loop",
    "ghe_thermal_loop",
]


def register(mcp: FastMCP) -> None:
    """Register des tools."""

    @mcp.tool(
        name="DF_DES_Create_Object",
        description=(
            "Create and persist any Dragonfly DES authoring object by kind: "
            "thermal_connector, horizontal_pipe_parameter, ghe_soil_parameter, "
            "ghe_fluid_parameter, ghe_pipe_parameter, ghe_borehole_parameter, "
            "ghe_design_parameter, ground_heat_exchanger, fourth_gen_thermal_loop, "
            "fifth_gen_thermal_loop, or ghe_thermal_loop. Thermal loops accept both "
            "saved parameter targets and inline parameter dictionaries directly."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "loop", "pipe", "target"},
        timeout=20,
    )
    def create_des_object(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        kind: Annotated[
            DesObjectKind,
            Field(description="DES authoring object kind matching garden.dragonfly_des.authoring.KIND_TO_CLASS."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the saved DES object target."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display name stored on SDK objects that support display_name."),
        ] = None,
        params: Annotated[
            dict[str, Any] | None,
            Field(description="Optional dictionary of kind-specific parameters merged with top-level arguments."),
        ] = None,
        polyline_points: Annotated[
            list[list[float]] | None,
            Field(description="Ordered 2D points [[x, y], ...] for thermal_connector."),
        ] = None,
        footprint_points: Annotated[
            list[list[float]] | None,
            Field(description="Ordered 2D footprint points [[x, y], ...] for ground_heat_exchanger."),
        ] = None,
        borehole_positions: Annotated[
            list[list[float]] | None,
            Field(description="Optional 3D borehole coordinates [[x, y, z], ...] for ground_heat_exchanger."),
        ] = None,
        connector_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="ThermalConnector targets for fifth_gen_thermal_loop or ghe_thermal_loop."),
        ] = None,
        ground_heat_exchanger_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="GroundHeatExchanger targets for ghe_thermal_loop."),
        ] = None,
        clockwise_flow: Annotated[
            bool | None,
            Field(description="Whether loop connector flow is clockwise (thermal loops)."),
        ] = None,
        soil_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved SoilParameter target or inline dict for fifth_gen_thermal_loop / ghe_thermal_loop."),
        ] = None,
        soil_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline SoilParameter parameter dictionary for thermal loops."),
        ] = None,
        horizontal_pipe_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved HorizontalPipeParameter target or inline dict for thermal loops."),
        ] = None,
        horizontal_pipe_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline HorizontalPipeParameter parameter dictionary for thermal loops."),
        ] = None,
        fluid_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved FluidParameter target or inline dict for ghe_thermal_loop."),
        ] = None,
        fluid_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline FluidParameter parameter dictionary for ghe_thermal_loop."),
        ] = None,
        pipe_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved PipeParameter target or inline dict for ghe_thermal_loop."),
        ] = None,
        pipe_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline PipeParameter parameter dictionary for ghe_thermal_loop."),
        ] = None,
        borehole_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved BoreholeParameter target or inline dict for ghe_thermal_loop."),
        ] = None,
        borehole_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline BoreholeParameter parameter dictionary for ghe_thermal_loop."),
        ] = None,
        design_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional saved GHEDesignParameter target or inline dict for ghe_thermal_loop."),
        ] = None,
        design_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline GHEDesignParameter parameter dictionary for ghe_thermal_loop."),
        ] = None,
        heat_rejection_type: Annotated[
            str | None,
            Field(description="Heat rejection type for fifth_gen_thermal_loop or ghe_thermal_loop."),
        ] = None,
        supplemental_heat_type: Annotated[
            str | None,
            Field(description="Supplemental heat type for fifth_gen_thermal_loop or ghe_thermal_loop."),
        ] = None,
        economizer_type: Annotated[
            str | None,
            Field(description="Economizer type for fourth_gen_thermal_loop."),
        ] = None,
        heating_type: Annotated[
            str | None,
            Field(description="Heating type for fourth_gen_thermal_loop."),
        ] = None,
        buried_depth: Annotated[
            float | None,
            Field(description="Buried depth in meters (horizontal_pipe_parameter or ghe_borehole_parameter)."),
        ] = None,
        diameter_ratio: Annotated[
            float | None,
            Field(description="Pipe diameter ratio 11-17 (horizontal_pipe_parameter)."),
        ] = None,
        pressure_drop_per_meter: Annotated[
            float | None,
            Field(description="Pressure drop per meter in Pa/m (horizontal_pipe_parameter)."),
        ] = None,
        insulation_conductivity: Annotated[
            float | None,
            Field(description="Insulation conductivity in W/m-K (horizontal_pipe_parameter)."),
        ] = None,
        insulation_thickness: Annotated[
            float | None,
            Field(description="Insulation thickness in meters (horizontal_pipe_parameter)."),
        ] = None,
        heat_capacity: Annotated[
            float | None,
            Field(description="Heat capacity in J/m3-K (horizontal_pipe_parameter, ghe_soil_parameter, or ghe_pipe_parameter)."),
        ] = None,
        roughness: Annotated[
            float | None,
            Field(description="Pipe roughness in meters (horizontal_pipe_parameter or ghe_pipe_parameter)."),
        ] = None,
        hydraulic_diameter: Annotated[
            float | None,
            Field(description="Optional hydraulic diameter in meters (horizontal_pipe_parameter)."),
        ] = None,
        pump_design_head: Annotated[
            float | None,
            Field(description="Optional pump design head in Pa (horizontal_pipe_parameter)."),
        ] = None,
        pump_flow_rate: Annotated[
            float | None,
            Field(description="Optional pump flow rate in m3/s (horizontal_pipe_parameter)."),
        ] = None,
        conductivity: Annotated[
            float | None,
            Field(description="Conductivity in W/m-K (ghe_soil_parameter or ghe_pipe_parameter)."),
        ] = None,
        undisturbed_temperature: Annotated[
            float | None,
            Field(description="Undisturbed ground temperature in C (ghe_soil_parameter)."),
        ] = None,
        grout_conductivity: Annotated[
            float | None,
            Field(description="Grout conductivity in W/m-K (ghe_soil_parameter)."),
        ] = None,
        grout_heat_capacity: Annotated[
            float | None,
            Field(description="Grout heat capacity in J/m3-K (ghe_soil_parameter)."),
        ] = None,
        fluid_type: Annotated[
            str | None,
            Field(description="Fluid type such as Water or EthyleneGlycol (ghe_fluid_parameter)."),
        ] = None,
        concentration: Annotated[
            float | None,
            Field(description="Fluid concentration percentage (ghe_fluid_parameter)."),
        ] = None,
        temperature: Annotated[
            float | None,
            Field(description="Fluid temperature in C (ghe_fluid_parameter)."),
        ] = None,
        inner_diameter: Annotated[
            float | None,
            Field(description="Borehole pipe inner diameter in meters (ghe_pipe_parameter)."),
        ] = None,
        outer_diameter: Annotated[
            float | None,
            Field(description="Borehole pipe outer diameter in meters (ghe_pipe_parameter)."),
        ] = None,
        shank_spacing: Annotated[
            float | None,
            Field(description="U-tube shank spacing in meters (ghe_pipe_parameter)."),
        ] = None,
        arrangement: Annotated[
            str | None,
            Field(description="Pipe arrangement such as SingleUTube (ghe_pipe_parameter)."),
        ] = None,
        min_depth: Annotated[
            float | None,
            Field(description="Minimum borehole depth in meters (ghe_borehole_parameter)."),
        ] = None,
        max_depth: Annotated[
            float | None,
            Field(description="Maximum borehole depth in meters (ghe_borehole_parameter)."),
        ] = None,
        min_spacing: Annotated[
            float | None,
            Field(description="Minimum borehole spacing in meters (ghe_borehole_parameter)."),
        ] = None,
        max_spacing: Annotated[
            float | None,
            Field(description="Maximum borehole spacing in meters (ghe_borehole_parameter)."),
        ] = None,
        diameter: Annotated[
            float | None,
            Field(description="Borehole diameter in meters (ghe_borehole_parameter)."),
        ] = None,
        flow_rate: Annotated[
            float | None,
            Field(description="GHE design flow rate (ghe_design_parameter)."),
        ] = None,
        flow_type: Annotated[
            str | None,
            Field(description="GHE design flow type such as Borehole (ghe_design_parameter)."),
        ] = None,
        max_eft: Annotated[
            float | None,
            Field(description="Maximum entering-fluid temperature in C (ghe_design_parameter)."),
        ] = None,
        min_eft: Annotated[
            float | None,
            Field(description="Minimum entering-fluid temperature in C (ghe_design_parameter)."),
        ] = None,
        month_count: Annotated[
            int | None,
            Field(description="Simulation month count for design sizing (ghe_design_parameter)."),
        ] = None,
        method: Annotated[
            str | None,
            Field(description="GHE design sizing method such as AreaProportional (ghe_design_parameter)."),
        ] = None,
        cooling_plant_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional CoolingPlant target for fourth_gen_thermal_loop."),
        ] = None,
        cooling_plant: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline CoolingPlant dict for fourth_gen_thermal_loop."),
        ] = None,
        heating_plant_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional HeatingPlant target for fourth_gen_thermal_loop."),
        ] = None,
        heating_plant: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline HeatingPlant dict for fourth_gen_thermal_loop."),
        ] = None,
        heat_recovery_chiller: Annotated[
            bool | None,
            Field(description="Whether fourth_gen_thermal_loop uses a heat recovery chiller."),
        ] = None,
        geojson_file_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative GeoJSON path for fifth_gen_thermal_loop or ghe_thermal_loop from_geojson import."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dict when loading a thermal loop from_geojson."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Optional [x, y] model origin when loading a thermal loop from_geojson."),
        ] = None,
        units: Annotated[
            str | None,
            Field(description="Optional model units string when loading a thermal loop from_geojson."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the serialized SDK object dict in addition to the compact target."),
        ] = False,
    ) -> dict[str, Any]:
        """Create and persist a Dragonfly DES authoring object."""
        from garden.dragonfly_des.authoring import create_des_object as service

        return service(
            garden_root=garden_root,
            kind=kind,
            identifier=identifier,
            params=params,
            display_name=display_name,
            include_body=include_body,
            polyline_points=polyline_points,
            footprint_points=footprint_points,
            borehole_positions=borehole_positions,
            connector_targets=connector_targets,
            ground_heat_exchanger_targets=ground_heat_exchanger_targets,
            clockwise_flow=clockwise_flow,
            soil_parameter_target=soil_parameter_target,
            soil_parameter=soil_parameter,
            horizontal_pipe_parameter_target=horizontal_pipe_parameter_target,
            horizontal_pipe_parameter=horizontal_pipe_parameter,
            fluid_parameter_target=fluid_parameter_target,
            fluid_parameter=fluid_parameter,
            pipe_parameter_target=pipe_parameter_target,
            pipe_parameter=pipe_parameter,
            borehole_parameter_target=borehole_parameter_target,
            borehole_parameter=borehole_parameter,
            design_parameter_target=design_parameter_target,
            design_parameter=design_parameter,
            heat_rejection_type=heat_rejection_type,
            supplemental_heat_type=supplemental_heat_type,
            economizer_type=economizer_type,
            heating_type=heating_type,
            cooling_plant_target=cooling_plant_target,
            cooling_plant=cooling_plant,
            heating_plant_target=heating_plant_target,
            heating_plant=heating_plant,
            heat_recovery_chiller=heat_recovery_chiller,
            geojson_file_path=geojson_file_path,
            location=location,
            point=point,
            units=units,
            buried_depth=buried_depth,
            diameter_ratio=diameter_ratio,
            pressure_drop_per_meter=pressure_drop_per_meter,
            insulation_conductivity=insulation_conductivity,
            insulation_thickness=insulation_thickness,
            heat_capacity=heat_capacity,
            roughness=roughness,
            hydraulic_diameter=hydraulic_diameter,
            pump_design_head=pump_design_head,
            pump_flow_rate=pump_flow_rate,
            conductivity=conductivity,
            undisturbed_temperature=undisturbed_temperature,
            grout_conductivity=grout_conductivity,
            grout_heat_capacity=grout_heat_capacity,
            fluid_type=fluid_type,
            concentration=concentration,
            temperature=temperature,
            inner_diameter=inner_diameter,
            outer_diameter=outer_diameter,
            shank_spacing=shank_spacing,
            arrangement=arrangement,
            min_depth=min_depth,
            max_depth=max_depth,
            min_spacing=min_spacing,
            max_spacing=max_spacing,
            diameter=diameter,
            flow_rate=flow_rate,
            flow_type=flow_type,
            max_eft=max_eft,
            min_eft=min_eft,
            month_count=month_count,
            method=method,
        )

    @mcp.tool(
        name="DF_DES_Export_Model",
        description=(
            "Export a Garden Dragonfly Model to URBANopt or DES handoff artifacts. "
            "Use export_kind='urbanopt' for feature GeoJSON + HBJSON artifacts (with "
            "optional DES thermal loop and Dragonfly Grid network/PV targets), or "
            "export_kind='des' for feature GeoJSON, scenario CSV, and system_params JSON."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "export", "artifact", "target"},
        timeout=60,
    )
    def export_des_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json; export artifacts are saved inside this Garden."),
        ],
        export_kind: Annotated[
            Literal["urbanopt", "des"],
            Field(description="Export target format: 'urbanopt' or 'des'."),
        ] = "urbanopt",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Specific Dragonfly Model target to export; omit to export the Garden base_dragonfly_model."),
        ] = None,
        des_loop_target: Annotated[
            dict[str, Any] | None,
            Field(description="DES thermal-loop target (required when export_kind='des'; optional when export_kind='urbanopt')."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden weather_file target with an EPW path (required when export_kind='des')."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dict (required when export_kind='urbanopt'; optional override for 'des')."),
        ] = None,
        electrical_network_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Grid electrical_network target to embed when export_kind='urbanopt'."),
        ] = None,
        road_network_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Grid road_network target to embed when export_kind='urbanopt'."),
        ] = None,
        ground_pv_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Grid ground_photovoltaics targets to embed when export_kind='urbanopt'."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Optional [x, y] model coordinate for the location marker."),
        ] = None,
        folder_name: Annotated[
            str | None,
            Field(description="Optional Garden export folder name."),
        ] = None,
        shade_distance: Annotated[
            float | None,
            Field(description="Optional shade search distance for export_kind='urbanopt'."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Keep Dragonfly Story multipliers as Honeybee Room multipliers (export_kind='urbanopt')."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Exclude generated plenum rooms (export_kind='urbanopt')."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Solve matching ceiling adjacencies (export_kind='urbanopt')."),
        ] = False,
        merge_method: Annotated[
            str,
            Field(description="Dragonfly Energy room merge method (export_kind='urbanopt')."),
        ] = "None",
        tolerance: Annotated[
            float | None,
            Field(description="Optional geometry tolerance for the Dragonfly Energy writer."),
        ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly Model to URBANopt or DES artifacts."""
        if export_kind == "des":
            if des_loop_target is None or weather_target is None:
                raise ValueError(
                    "DF_DES_Export_Model with export_kind='des' requires des_loop_target and weather_target."
                )
            from garden.dragonfly_des.export import export_model_to_des as service

            return service(
                garden_root=garden_root,
                des_loop_target=des_loop_target,
                weather_target=weather_target,
                model_target=model_target,
                location=location,
                point=point,
                folder_name=folder_name,
                tolerance=tolerance,
            )

        if location is None:
            raise ValueError(
                "DF_DES_Export_Model with export_kind='urbanopt' requires location."
            )
        from garden.dragonfly_des.export import export_urbanopt_model as service

        return service(
            garden_root=garden_root,
            location=location,
            model_target=model_target,
            des_loop_target=des_loop_target,
            electrical_network_target=electrical_network_target,
            road_network_target=road_network_target,
            ground_pv_targets=ground_pv_targets,
            point=point,
            folder_name=folder_name,
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_DES_Run_Step",
        description=(
            "Run one post-URBANopt DES workflow step: assign_building_loads, sys_param, "
            "write_modelica_project, or modelica_simulation. Asynchronous steps write a "
            "Garden run ledger with poll_next pointing to GD_Poll_Run and optionally accept "
            "wait_seconds to wait for completion in one call."
        ),
        tags={"dragonfly", "district-energy", "run", "runtime", "sizing", "simulate", "target"},
        timeout=300,
    )
    def run_des_step(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        step: Annotated[
            Literal[
                "assign_building_loads",
                "sys_param",
                "write_modelica_project",
                "modelica_simulation",
                "check_compatibility",
                "bind_des_loads",
                "read_ghe_results",
            ],
            Field(description="DES workflow step to execute."),
        ],
        feature_geojson_target: Annotated[
            dict[str, Any] | None,
            Field(description="DES feature GeoJSON artifact target (required for assign_building_loads, sys_param, write_modelica_project, and check_compatibility)."),
        ] = None,
        scenario_csv_target: Annotated[
            dict[str, Any] | None,
            Field(description="DES scenario CSV artifact target (required for assign_building_loads, sys_param, write_modelica_project; optional for bind_des_loads)."),
        ] = None,
        system_parameter_json_target: Annotated[
            dict[str, Any] | None,
            Field(description="DES system_params JSON artifact target (optional for sys_param; required for write_modelica_project)."),
        ] = None,
        modelica_project_target: Annotated[
            dict[str, Any] | None,
            Field(description="DES Modelica project artifact target (required for modelica_simulation)."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target for step='bind_des_loads'."),
        ] = None,
        heat_exchanger_ets_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional HeatExchangerETS target for step='bind_des_loads'."),
        ] = None,
        heat_exchanger_ets: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline HeatExchangerETS dict for step='bind_des_loads'."),
        ] = None,
        heat_pump_ets_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional HeatPumpETS target for step='bind_des_loads'."),
        ] = None,
        heat_pump_ets: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline HeatPumpETS dict for step='bind_des_loads'."),
        ] = None,
        building_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Building identifiers to assign ETS objects in step='bind_des_loads'."),
        ] = None,
        ghe_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional GroundHeatExchanger target for coordinate matching in step='read_ghe_results'."),
        ] = None,
        ghe_folder: Annotated[
            str | None,
            Field(description="Optional Garden-relative folder containing GHEDesigner outputs for step='read_ghe_results'."),
        ] = None,
        borehole_file: Annotated[
            str | None,
            Field(description="Optional Garden-relative BoreFieldData.csv path for step='read_ghe_results'."),
        ] = None,
        g_function_file: Annotated[
            str | None,
            Field(description="Optional Garden-relative Gfunction.csv path for step='read_ghe_results'."),
        ] = None,
        summary_file: Annotated[
            str | None,
            Field(description="Optional Garden-relative SimulationSummary.json path for step='read_ghe_results'."),
        ] = None,
        units: Annotated[
            str,
            Field(description="Model units when loading GHE boreholes in step='read_ghe_results'."),
        ] = "Meters",
        ortho_rotation: Annotated[
            bool,
            Field(description="Whether to ortho-rotate ThermalNetwork borehole coordinates in step='read_ghe_results'."),
        ] = False,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run id for ledger-backed steps."),
        ] = None,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional seconds to poll asynchronous steps (sys_param, modelica_simulation) before returning."),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is provided."),
        ] = 2.0,
    ) -> dict[str, Any]:
        """Run one DES workflow step."""
        if step == "check_compatibility":
            if feature_geojson_target is None:
                raise ValueError("step='check_compatibility' requires feature_geojson_target.")
            from garden.dragonfly_des.runs import check_des_compatibility_service as service

            return service(
                garden_root=garden_root,
                feature_geojson_target=feature_geojson_target,
            )

        if step == "bind_des_loads":
            from garden.dragonfly_des.runs import bind_des_loads_to_model as service

            return service(
                garden_root=garden_root,
                model_target=model_target,
                scenario_csv_target=scenario_csv_target,
                heat_exchanger_ets_target=heat_exchanger_ets_target,
                heat_exchanger_ets=heat_exchanger_ets,
                heat_pump_ets_target=heat_pump_ets_target,
                heat_pump_ets=heat_pump_ets,
                building_identifiers=building_identifiers,
            )

        if step == "read_ghe_results":
            from garden.dragonfly_des.runs import read_ghe_results as service

            return service(
                garden_root=garden_root,
                ghe_target=ghe_target,
                ghe_folder=ghe_folder,
                borehole_file=borehole_file,
                g_function_file=g_function_file,
                summary_file=summary_file,
                units=units,
                ortho_rotation=ortho_rotation,
            )

        if step == "assign_building_loads":
            if feature_geojson_target is None or scenario_csv_target is None:
                raise ValueError(
                    "step='assign_building_loads' requires feature_geojson_target and scenario_csv_target."
                )
            from garden.dragonfly_des.runs import assign_building_loads as service

            return service(
                garden_root=garden_root,
                feature_geojson_target=feature_geojson_target,
                scenario_csv_target=scenario_csv_target,
            )

        if step == "sys_param":
            if feature_geojson_target is None or scenario_csv_target is None:
                raise ValueError(
                    "step='sys_param' requires feature_geojson_target and scenario_csv_target."
                )
            from garden.dragonfly_des.runs import start_sys_param as service

            return service(
                garden_root=garden_root,
                feature_geojson_target=feature_geojson_target,
                scenario_csv_target=scenario_csv_target,
                system_parameter_json_target=system_parameter_json_target,
                run_id=run_id,
                wait_seconds=wait_seconds,
                poll_interval=poll_interval,
            )

        if step == "write_modelica_project":
            if (
                system_parameter_json_target is None
                or feature_geojson_target is None
                or scenario_csv_target is None
            ):
                raise ValueError(
                    "step='write_modelica_project' requires system_parameter_json_target, "
                    "feature_geojson_target, and scenario_csv_target."
                )
            from garden.dragonfly_des.runs import write_modelica_project as service

            return service(
                garden_root=garden_root,
                system_parameter_json_target=system_parameter_json_target,
                feature_geojson_target=feature_geojson_target,
                scenario_csv_target=scenario_csv_target,
                run_id=run_id,
            )

        if modelica_project_target is None:
            raise ValueError("step='modelica_simulation' requires modelica_project_target.")
        from garden.dragonfly_des.runs import start_modelica_simulation as service

        return service(
            garden_root=garden_root,
            modelica_project_target=modelica_project_target,
            run_id=run_id,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
        )
