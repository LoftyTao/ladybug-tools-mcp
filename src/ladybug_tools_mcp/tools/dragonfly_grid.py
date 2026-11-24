"""dragonfly_grid MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactTargetRef,
    GardenTargetRef,
    MutationResultModel,
    QueryResultModel,
    RunResultModel,
    RunTargetRef,
    dump_input,
    dump_target,
    dump_targets,
    validate_output,
)


GridObjectKind = Literal[
    "substation",
    "transformer",
    "electrical_connector",
    "electrical_network",
    "road_network",
    "ground_photovoltaics",
    "financial_parameters",
    "wire",
    "power_line",
    "transformer_properties",
    "reopt_parameter",
]


def register(mcp: FastMCP) -> None:
    """Register dragonfly_grid tools."""

    @mcp.tool(
        name="DF_Grid_Create_Object",
        description=(
            "Create and persist a Dragonfly Electric Grid object by kind: substation, "
            "transformer, electrical_connector, electrical_network, road_network, "
            "ground_photovoltaics, or financial_parameters. Use LB_Search_Standards_Library "
            "to look up OpenDSS transformer_properties and power_lines catalog identifiers."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "reopt", "rnm", "author", "target"},
        timeout=20,
    )
    def create_grid_object(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        kind: Annotated[
            GridObjectKind,
            Field(description="Dragonfly Electric Grid object kind."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the saved Grid object target."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display name stored on the SDK object."),
        ] = None,
        footprint_points: Annotated[
            list[list[float]] | None,
            Field(description="2D footprint points [[x, y], ...] for substation, transformer, or ground_photovoltaics."),
        ] = None,
        polyline_points: Annotated[
            list[list[float]] | None,
            Field(description="2D polyline points [[x, y], ...] for electrical_connector."),
        ] = None,
        transformer_properties_identifier: Annotated[
            str | None,
            Field(description="OpenDSS transformer properties identifier from LB_Search_Standards_Library (for transformer)."),
        ] = None,
        transformer_properties_target: Annotated[
            GardenTargetRef | None,
            Field(description="Optional custom transformer_properties target (from kind='transformer_properties')."),
        ] = None,
        power_line_identifier: Annotated[
            str | None,
            Field(description="OpenDSS power-line identifier from LB_Search_Standards_Library (for electrical_connector)."),
        ] = None,
        power_line_target: Annotated[
            GardenTargetRef | None,
            Field(description="Optional custom power_line target (from kind='power_line')."),
        ] = None,
        substation_target: Annotated[
            GardenTargetRef | None,
            Field(description="Substation target for electrical_network or road_network."),
        ] = None,
        transformer_targets: Annotated[
            list[GardenTargetRef] | None,
            Field(description="Transformer targets for electrical_network."),
        ] = None,
        connector_targets: Annotated[
            list[GardenTargetRef] | None,
            Field(description="ElectricalConnector targets for electrical_network."),
        ] = None,
        road_segments: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Road segment dicts {identifier, polyline_points} for road_network."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Optional Dragonfly Building identifier associated with ground_photovoltaics."),
        ] = None,
        analysis_years: Annotated[
            int,
            Field(description="REopt analysis period in years (for financial_parameters).", ge=1),
        ] = 25,
        escalation_rate: Annotated[
            float,
            Field(description="Annual escalation rate fraction (for financial_parameters)."),
        ] = 0.023,
        tax_rate: Annotated[
            float,
            Field(description="Tax rate fraction (for financial_parameters).", ge=0, le=1),
        ] = 0.26,
        discount_rate: Annotated[
            float,
            Field(description="Discount rate fraction (for financial_parameters)."),
        ] = 0.083,
        geojson_file_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative RNM GeoJSON path for electrical_network from_rnm_geojson."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dict when loading electrical_network from RNM GeoJSON."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Optional [x, y] coordinate origin when loading electrical_network from RNM GeoJSON."),
        ] = None,
        units: Annotated[
            str,
            Field(description="Model units when loading electrical_network from RNM GeoJSON."),
        ] = "Meters",
        ampacity: Annotated[
            float,
            Field(description="Wire ampacity (A) for kind='wire'.", gt=0),
        ] = 220,
        geometrical_mean_radius: Annotated[
            float,
            Field(description="Wire GMR (mm) for kind='wire'.", gt=0),
        ] = 3.9,
        resistance: Annotated[
            float,
            Field(description="Resistance (Ohm/km or per-unit) for wire or transformer_properties.", gt=0),
        ] = 0.3937,
        diameter: Annotated[
            float,
            Field(description="Wire diameter (mm) for kind='wire'.", gt=0),
        ] = 10,
        voltage_level: Annotated[
            Literal["LV", "MV", "LV or MV"],
            Field(description="Voltage level ('MV' or 'LV') for kind='wire'."),
        ] = "MV",
        wire_type: Annotated[
            Literal["OH", "UG", "UG concentric neutral"],
            Field(description="Wire type ('OH' or 'UG') for kind='wire'."),
        ] = "OH",
        concentric_properties: Annotated[
            dict[str, Any] | None,
            Field(description="Optional ConcentricProperties fields dict for underground kind='wire'."),
        ] = None,
        wires: Annotated[
            list[GardenTargetRef | str] | None,
            Field(description="Wire targets, dicts, or catalog IDs for kind='power_line'."),
        ] = None,
        heights: Annotated[
            list[float] | None,
            Field(description="Wire vertical heights (m) for kind='power_line'."),
        ] = None,
        relative_xs: Annotated[
            list[float] | None,
            Field(description="Wire horizontal offsets (m) for kind='power_line'."),
        ] = None,
        phases: Annotated[
            list[str] | None,
            Field(description="Phase labels (e.g. ['A','B','C','N']) for kind='power_line'."),
        ] = None,
        phase_count: Annotated[
            int | None,
            Field(description="Phase count for power_line or transformer_properties.", ge=1, le=3),
        ] = None,
        nominal_voltage: Annotated[
            float | None,
            Field(description="Optional nominal voltage for kind='power_line'.", gt=0),
        ] = None,
        kva: Annotated[
            float | None,
            Field(description="kVA rating for kind='transformer_properties'.", gt=0),
        ] = None,
        reactance: Annotated[
            float,
            Field(description="Per-unit reactance for kind='transformer_properties'.", ge=0),
        ] = 0.1,
        high_voltage: Annotated[
            float,
            Field(description="High-side voltage (kV) for kind='transformer_properties'.", gt=0),
        ] = 13.2,
        low_voltage: Annotated[
            float,
            Field(description="Low-side voltage (kV) for kind='transformer_properties'.", gt=0),
        ] = 0.48,
        is_center_tap: Annotated[
            bool,
            Field(description="Center-tap flag for kind='transformer_properties'."),
        ] = False,
        connection: Annotated[
            Literal["Wye-Wye", "Wye-Delta", "Delta-Wye", "Delta-Delta"],
            Field(description="Winding connection (e.g. Wye-Wye) for kind='transformer_properties'."),
        ] = "Wye-Wye",
        financial_parameters_target: Annotated[
            GardenTargetRef | None,
            Field(description="Optional FinancialParameter target for kind='reopt_parameter'."),
        ] = None,
        financial_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional FinancialParameter dict for kind='reopt_parameter'."),
        ] = None,
        pv_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional PVParameter dict for kind='reopt_parameter'."),
        ] = None,
        storage_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional StorageParameter dict for kind='reopt_parameter'."),
        ] = None,
        wind_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional WindParameter dict for kind='reopt_parameter'."),
        ] = None,
        generator_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional GeneratorParameter dict for kind='reopt_parameter'."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the serialized SDK object dict in addition to the compact target."),
        ] = False,
    ) -> MutationResultModel:
        """Create and persist a Dragonfly Electric Grid object."""
        from garden.dragonfly_grid import authoring

        dumped_transformer_properties_target = dump_target(transformer_properties_target)
        dumped_power_line_target = dump_target(power_line_target)
        dumped_substation_target = dump_target(substation_target)

        if kind == "substation":
            if footprint_points is None:
                raise ValueError("kind='substation' requires footprint_points.")
            return validate_output(
                MutationResultModel,
                authoring.create_substation(
                    garden_root=garden_root,
                    identifier=identifier,
                    footprint_points=footprint_points,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "transformer":
            if footprint_points is None or (
                transformer_properties_identifier is None
                and dumped_transformer_properties_target is None
            ):
                raise ValueError(
                    "kind='transformer' requires footprint_points and either "
                    "transformer_properties_identifier or transformer_properties_target."
                )
            return validate_output(
                MutationResultModel,
                authoring.create_transformer(
                    garden_root=garden_root,
                    identifier=identifier,
                    footprint_points=footprint_points,
                    transformer_properties_identifier=transformer_properties_identifier,
                    transformer_properties_target=dumped_transformer_properties_target,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "electrical_connector":
            if polyline_points is None or (
                power_line_identifier is None and dumped_power_line_target is None
            ):
                raise ValueError(
                    "kind='electrical_connector' requires polyline_points and either "
                    "power_line_identifier or power_line_target."
                )
            return validate_output(
                MutationResultModel,
                authoring.create_electrical_connector(
                    garden_root=garden_root,
                    identifier=identifier,
                    polyline_points=polyline_points,
                    power_line_identifier=power_line_identifier,
                    power_line_target=dumped_power_line_target,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "electrical_network":
            return validate_output(
                MutationResultModel,
                authoring.create_electrical_network(
                    garden_root=garden_root,
                    identifier=identifier,
                    substation_target=dumped_substation_target,
                    transformer_targets=dump_targets(transformer_targets),
                    connector_targets=dump_targets(connector_targets),
                    geojson_file_path=geojson_file_path,
                    location=dump_input(location),
                    point=point,
                    units=units,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "road_network":
            if dumped_substation_target is None or road_segments is None:
                raise ValueError("kind='road_network' requires substation_target and road_segments.")
            return validate_output(
                MutationResultModel,
                authoring.create_road_network(
                    garden_root=garden_root,
                    identifier=identifier,
                    substation_target=dumped_substation_target,
                    road_segments=dump_input(road_segments),
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "ground_photovoltaics":
            if footprint_points is None:
                raise ValueError("kind='ground_photovoltaics' requires footprint_points.")
            return validate_output(
                MutationResultModel,
                authoring.create_ground_photovoltaics(
                    garden_root=garden_root,
                    identifier=identifier,
                    footprint_points=footprint_points,
                    building_identifier=building_identifier,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "wire":
            return validate_output(
                MutationResultModel,
                authoring.create_wire(
                    garden_root=garden_root,
                    identifier=identifier,
                    ampacity=ampacity,
                    geometrical_mean_radius=geometrical_mean_radius,
                    resistance=resistance,
                    diameter=diameter,
                    voltage_level=voltage_level,
                    wire_type=wire_type,
                    concentric_properties=dump_input(concentric_properties),
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "power_line":
            if wires is None or heights is None or relative_xs is None or phases is None:
                raise ValueError(
                    "kind='power_line' requires wires, heights, relative_xs, and phases."
                )
            return validate_output(
                MutationResultModel,
                authoring.create_power_line(
                    garden_root=garden_root,
                    identifier=identifier,
                    wires=dump_input(wires),
                    heights=heights,
                    relative_xs=relative_xs,
                    phases=phases,
                    phase_count=phase_count,
                    nominal_voltage=nominal_voltage,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "transformer_properties":
            if kva is None:
                raise ValueError("kind='transformer_properties' requires kva.")
            return validate_output(
                MutationResultModel,
                authoring.create_transformer_properties(
                    garden_root=garden_root,
                    identifier=identifier,
                    kva=kva,
                    resistance=0.1 if resistance == 0.3937 else resistance,
                    reactance=reactance,
                    phase_count=phase_count or 3,
                    high_voltage=high_voltage,
                    low_voltage=low_voltage,
                    is_center_tap=is_center_tap,
                    connection=connection,
                    display_name=display_name,
                    include_body=include_body,
                ),
            )
        if kind == "reopt_parameter":
            return validate_output(
                MutationResultModel,
                authoring.create_reopt_parameter(
                    garden_root=garden_root,
                    identifier=identifier,
                    financial_parameters_target=dump_target(financial_parameters_target),
                    financial_parameter=dump_input(financial_parameter),
                    pv_parameter=dump_input(pv_parameter),
                    storage_parameter=dump_input(storage_parameter),
                    wind_parameter=dump_input(wind_parameter),
                    generator_parameter=dump_input(generator_parameter),
                    include_body=include_body,
                ),
            )
        return validate_output(
            MutationResultModel,
            authoring.create_financial_parameters(
                garden_root=garden_root,
                identifier=identifier,
                analysis_years=analysis_years,
                escalation_rate=escalation_rate,
                tax_rate=tax_rate,
                discount_rate=discount_rate,
                include_body=include_body,
            ),
        )

    @mcp.tool(
        name="DF_Grid_Start_Simulation",
        description=(
            "Start or block a Dragonfly Electric Grid OpenDSS, REopt, or RNM run from "
            "feature GeoJSON and scenario CSV targets. Writes a Garden run ledger with "
            "poll_next pointing to GD_Poll_Run, and optionally accepts wait_seconds to "
            "wait for completion in one call."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "reopt", "rnm", "run", "runtime", "target"},
        timeout=300,
    )
    def start_grid_simulation(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json; the run ledger is written inside this Garden."),
        ],
        engine: Annotated[
            Literal["opendss", "reopt", "rnm"],
            Field(description="Grid simulation engine: 'opendss', 'reopt', or 'rnm'."),
        ],
        feature_geojson_target: Annotated[
            ArtifactTargetRef,
            Field(description="Feature GeoJSON artifact target for the Grid project."),
        ],
        scenario_csv_target: Annotated[
            ArtifactTargetRef,
            Field(description="Scenario CSV artifact target paired with the feature GeoJSON."),
        ],
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run id; omit to let the Garden create one."),
        ] = None,
        autosize: Annotated[
            bool,
            Field(description="Whether to request OpenDSS network upgrade/autosizing (engine='opendss')."),
        ] = False,
        urdb_label: Annotated[
            str | None,
            Field(description="URDB utility rate label (required when engine='reopt')."),
        ] = None,
        developer_key: Annotated[
            str | None,
            Field(description="Optional REopt developer key (redacted in reports; engine='reopt')."),
        ] = None,
        financial_parameters_target: Annotated[
            GardenTargetRef | None,
            Field(description="Optional saved FinancialParameter target for engine='reopt'."),
        ] = None,
        financial_parameters: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline FinancialParameter dict for engine='reopt'."),
        ] = None,
        reopt_parameter_target: Annotated[
            GardenTargetRef | None,
            Field(description="Optional saved REoptParameter target for engine='reopt'."),
        ] = None,
        reopt_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline REoptParameter dict for engine='reopt'."),
        ] = None,
        underground_ratio: Annotated[
            float,
            Field(description="RNM underground ratio (engine='rnm').", ge=0, le=1),
        ] = 0.9,
        lv_only: Annotated[
            bool,
            Field(description="Whether RNM should run low-voltage-only network generation (engine='rnm')."),
        ] = True,
        nodes_per_building: Annotated[
            int,
            Field(description="RNM nodes per building (engine='rnm').", ge=1),
        ] = 1,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional seconds to poll for completion before returning; omit to return immediately.", ge=0),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is provided.", gt=0),
        ] = 2.0,
    ) -> RunResultModel:
        """Start or block an OpenDSS, REopt, or RNM simulation run."""
        from garden.dragonfly_grid import runs

        dumped_feature = dump_target(feature_geojson_target) or {}
        dumped_scenario = dump_target(scenario_csv_target) or {}

        if engine == "opendss":
            return validate_output(
                RunResultModel,
                runs.start_opendss(
                    garden_root=garden_root,
                    feature_geojson_target=dumped_feature,
                    scenario_csv_target=dumped_scenario,
                    run_id=run_id,
                    autosize=autosize,
                    wait_seconds=wait_seconds,
                    poll_interval=poll_interval,
                ),
            )
        if engine == "reopt":
            if not urdb_label:
                raise ValueError("engine='reopt' requires urdb_label.")
            return validate_output(
                RunResultModel,
                runs.start_reopt(
                    garden_root=garden_root,
                    feature_geojson_target=dumped_feature,
                    scenario_csv_target=dumped_scenario,
                    urdb_label=urdb_label,
                    financial_parameters_target=dump_target(financial_parameters_target),
                    financial_parameters=dump_input(financial_parameters),
                    reopt_parameter_target=dump_target(reopt_parameter_target),
                    reopt_parameter=dump_input(reopt_parameter),
                    run_id=run_id,
                    developer_key=developer_key,
                    wait_seconds=wait_seconds,
                    poll_interval=poll_interval,
                ),
            )
        return validate_output(
            RunResultModel,
            runs.start_rnm(
                garden_root=garden_root,
                feature_geojson_target=dumped_feature,
                scenario_csv_target=dumped_scenario,
                run_id=run_id,
                underground_ratio=underground_ratio,
                lv_only=lv_only,
                nodes_per_building=nodes_per_building,
                wait_seconds=wait_seconds,
                poll_interval=poll_interval,
            ),
        )

    @mcp.tool(
        name="DF_Grid_Results",
        description=(
            "Read OpenDSS CSV results or build VisualizationSet handoffs for Grid "
            "networks and results: action='read_opendss_result', 'network_to_vis_set', "
            "or 'results_to_vis_set'. Use LB_Export_Visualization_Set to export "
            "resulting VisualizationSets to HTML, SVG, or vtk.js."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "result", "visualization", "visualization-set", "target"},
        timeout=20,
    )
    def grid_results(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        action: Annotated[
            Literal[
                "read_opendss_result",
                "read_reopt_result",
                "network_to_vis_set",
                "results_to_vis_set",
            ],
            Field(description="Grid result action: 'read_opendss_result', 'read_reopt_result', 'network_to_vis_set', or 'results_to_vis_set'."),
        ],
        result_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Registered OpenDSS CSV result artifact target (action='read_opendss_result')."),
        ] = None,
        result_targets: Annotated[
            list[ArtifactTargetRef] | None,
            Field(description="Registered OpenDSS CSV result artifact targets."),
        ] = None,
        network_target: Annotated[
            GardenTargetRef | None,
            Field(description="ElectricalNetwork target (for 'network_to_vis_set' or matching geometry in 'results_to_vis_set')."),
        ] = None,
        attr_name: Annotated[
            str,
            Field(description="Network equipment attribute to visualize for action='network_to_vis_set'."),
        ] = "identifier",
        attribute: Annotated[
            str | int,
            Field(description="Collection aggregation ('max', 'min', 'average', 'total', or integer step) for 'results_to_vis_set'."),
        ] = "max",
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Completed REopt run_target for action='read_reopt_result'."),
        ] = None,
        report_json_path: Annotated[
            str | None,
            Field(description="Garden-relative scenario_optimization.json path for action='read_reopt_result'."),
        ] = None,
        report_csv_path: Annotated[
            str | None,
            Field(description="Garden-relative scenario_optimization.csv path for action='read_reopt_result'."),
        ] = None,
        max_rows: Annotated[
            int,
            Field(description="Maximum preview rows to return for action='read_opendss_result'.", ge=1),
        ] = 25,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict; keep false for compact target handoff."),
        ] = False,
    ) -> QueryResultModel:
        """Read OpenDSS/REopt results or convert Grid networks/results to VisualizationSets."""
        from garden.dragonfly_grid import authoring

        dumped_result_target = dump_target(result_target)
        dumped_result_targets = dump_targets(result_targets)
        dumped_network_target = dump_target(network_target)
        dumped_run_target = dump_target(run_target)

        if action == "read_opendss_result":
            if dumped_result_target is None and dumped_result_targets is None:
                raise ValueError("action='read_opendss_result' requires result_target or result_targets.")
            return validate_output(
                QueryResultModel,
                authoring.read_opendss_result(
                    garden_root=garden_root,
                    result_target=dumped_result_target,
                    result_targets=dumped_result_targets,
                    max_rows=max_rows,
                ),
            )
        if action == "read_reopt_result":
            return validate_output(
                QueryResultModel,
                authoring.read_reopt_result(
                    garden_root=garden_root,
                    report_json_path=report_json_path,
                    report_csv_path=report_csv_path,
                    run_target=dumped_run_target,
                ),
            )
        if action == "network_to_vis_set":
            if dumped_network_target is None:
                raise ValueError("action='network_to_vis_set' requires network_target.")
            return validate_output(
                QueryResultModel,
                authoring.grid_network_to_visualization_set(
                    garden_root=garden_root,
                    network_target=dumped_network_target,
                    attr_name=attr_name,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )
        if dumped_result_targets is None:
            raise ValueError("action='results_to_vis_set' requires result_targets.")
        return validate_output(
            QueryResultModel,
            authoring.grid_results_to_visualization_set(
                garden_root=garden_root,
                result_targets=dumped_result_targets,
                network_target=dumped_network_target,
                attribute=attribute,
                name=name or "OpenDSS Results",
                return_visualization_set=return_visualization_set,
            ),
        )
