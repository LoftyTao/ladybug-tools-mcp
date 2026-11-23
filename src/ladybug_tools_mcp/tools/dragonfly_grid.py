"""dragonfly_grid MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register dragonfly_grid tools."""

    @mcp.tool(
        name="DF_Grid_Electrical_Connector",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS ElectricalConnector from "
            "2D polyline points and a power-line identifier returned by "
            "DF_Grid_Search_OpenDSS. Use the target in DF_Grid_Electrical_Network."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "connector", "author", "target"},
        timeout=20,
    )
    def create_electrical_connector(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid ElectricalConnector target.")],
        polyline_points: Annotated[list[list[float]], Field(description="Ordered 2D connector points as [[x, y], ...].")],
        power_line_identifier: Annotated[str, Field(description="OpenDSS power-line identifier from DF_Grid_Search_OpenDSS.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid ElectricalConnector."""
        from garden.dragonfly_grid.authoring import create_electrical_connector as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            polyline_points=polyline_points,
            power_line_identifier=power_line_identifier,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Electrical_Network",
        description=(
            "Create a Dragonfly Electric Grid ElectricalNetwork from a Substation "
            "target plus Transformer and ElectricalConnector targets. Pass the "
            "returned target into Dragonfly-to-GeoJSON/export workflows when grid "
            "export support is available."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "network", "author", "target"},
        timeout=20,
    )
    def create_electrical_network(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the ElectricalNetwork target.")],
        substation_target: Annotated[dict[str, Any], Field(description="Target returned by DF_Grid_Substation.")],
        transformer_targets: Annotated[list[dict[str, Any]], Field(description="Transformer targets returned by DF_Grid_Transformer.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="ElectricalConnector targets returned by DF_Grid_Electrical_Connector.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid ElectricalNetwork."""
        from garden.dragonfly_grid.authoring import create_electrical_network as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            substation_target=substation_target,
            transformer_targets=transformer_targets,
            connector_targets=connector_targets,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Financial_Parameters",
        description=(
            "Create Dragonfly Energy REopt FinancialParameter settings for "
            "Grid/REopt workflows. This authors financial assumptions only; use "
            "DF_Grid_Start_REopt for runtime-gated REopt execution. Returns "
            "target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "electric-grid", "reopt", "financial", "author", "target"},
        timeout=20,
    )
    def create_financial_parameters(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the FinancialParameter target.")],
        analysis_years: Annotated[int, Field(description="REopt analysis period in years.")] = 25,
        escalation_rate: Annotated[float, Field(description="Annual escalation rate fraction.")] = 0.023,
        tax_rate: Annotated[float, Field(description="Tax rate fraction.")] = 0.26,
        discount_rate: Annotated[float, Field(description="Discount rate fraction.")] = 0.083,
    ) -> dict[str, Any]:
        """Create Dragonfly Energy REopt FinancialParameter settings."""
        from garden.dragonfly_grid.authoring import create_financial_parameters as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            analysis_years=analysis_years,
            escalation_rate=escalation_rate,
            tax_rate=tax_rate,
            discount_rate=discount_rate,
        )

    @mcp.tool(
        name="DF_Grid_Ground_Photovoltaics",
        description=(
            'Create a Dragonfly Energy REopt GroundMountPV object from footprint points. This '
            'authors PV geometry for Grid/REopt export handoff. Returns target, summary_view, '
            'persistence_receipt, and report.'
        ),
        tags={"dragonfly", "electric-grid", "reopt", "photovoltaic", "pv", "author", "target"},
        timeout=20,
    )
    def create_ground_photovoltaics(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the GroundMountPV target.")],
        footprint_points: Annotated[list[list[float]], Field(description="2D ground-mounted PV footprint points as [[x, y], ...].")],
        building_identifier: Annotated[str | None, Field(description="Optional Dragonfly Building identifier associated with this PV system.")] = None,
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Energy GroundMountPV object."""
        from garden.dragonfly_grid.authoring import create_ground_photovoltaics as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            building_identifier=building_identifier,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Road_Network",
        description=(
            "Create a Dragonfly Electric Grid RNM RoadNetwork from a Substation "
            "target and road segment dictionaries. Road segments use "
            "{identifier, polyline_points}. Returns a compact target for RNM workflows."
        ),
        tags={"dragonfly", "electric-grid", "rnm", "road", "network", "author", "target"},
        timeout=20,
    )
    def create_road_network(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the RoadNetwork target.")],
        substation_target: Annotated[dict[str, Any], Field(description="Target returned by DF_Grid_Substation.")],
        road_segments: Annotated[list[dict[str, Any]], Field(description="Road segment dicts with identifier and polyline_points fields.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid RoadNetwork."""
        from garden.dragonfly_grid.authoring import create_road_network as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            substation_target=substation_target,
            road_segments=road_segments,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Substation",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS Substation from "
            "Grasshopper-style footprint points. Use the returned target in "
            "DF_Grid_Electrical_Network or DF_Grid_Road_Network. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "author", "target"},
        timeout=20,
    )
    def create_substation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid Substation target.")],
        footprint_points: Annotated[list[list[float]], Field(description="Closed or open 2D footprint points as [[x, y], ...].")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid Substation."""
        from garden.dragonfly_grid.authoring import create_substation as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Transformer",
        description=(
            "Create a Dragonfly Electric Grid OpenDSS Transformer from footprint "
            "points and an OpenDSS transformer properties identifier returned by "
            "DF_Grid_Search_OpenDSS. Returns a compact Grid target for network assembly."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "transformer", "author", "target"},
        timeout=20,
    )
    def create_transformer(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Grid Transformer target.")],
        footprint_points: Annotated[list[list[float]], Field(description="2D transformer footprint points as [[x, y], ...].")],
        transformer_properties_identifier: Annotated[str, Field(description="OpenDSS transformer properties identifier from DF_Grid_Search_OpenDSS.")],
        display_name: Annotated[str | None, Field(description="Optional display name stored on the SDK object.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Electric Grid Transformer."""
        from garden.dragonfly_grid.authoring import create_transformer as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            transformer_properties_identifier=transformer_properties_identifier,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Grid_Network_To_Visualization_Set",
        description=(
            "Create a compact Ladybug Display VisualizationSet target for a "
            "Dragonfly Electric Grid ElectricalNetwork. Use the returned "
            "visualization_set_target with shared visualization exporters."
        ),
        tags={"dragonfly", "electric-grid", "visualization", "visualization-set", "target"},
        timeout=20,
    )
    def grid_network_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        network_target: Annotated[dict[str, Any], Field(description="ElectricalNetwork target returned by DF_Grid_Electrical_Network.")],
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/display name.")] = None,
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict; keep false for compact target handoff.")] = False,
    ) -> dict[str, Any]:
        """Create a VisualizationSet target for an Electric Grid network."""
        from garden.dragonfly_grid.authoring import grid_network_to_visualization_set as service

        return service(
            garden_root=garden_root,
            network_target=network_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Grid_Results_To_Visualization_Set",
        description=(
            "Create a compact Ladybug Display VisualizationSet target for "
            "registered Dragonfly Grid OpenDSS result artifacts. Use shared "
            "visualization exporters for SVG, HTML, or vtk.js output."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "result", "visualization", "visualization-set", "target"},
        timeout=20,
    )
    def grid_results_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        result_targets: Annotated[list[dict[str, Any]], Field(description="Registered OpenDSS CSV result artifact targets.")],
        name: Annotated[str, Field(description="VisualizationSet identifier/display name.")] = "OpenDSS Results",
        return_visualization_set: Annotated[bool, Field(description="Return the full VisualizationSet dict; keep false for compact target handoff.")] = False,
    ) -> dict[str, Any]:
        """Create a VisualizationSet target for Electric Grid result artifacts."""
        from garden.dragonfly_grid.authoring import grid_results_to_visualization_set as service

        return service(
            garden_root=garden_root,
            result_targets=result_targets,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Grid_Read_OpenDSS_Result",
        description=(
            "Read a registered Dragonfly Grid OpenDSS CSV result artifact into a "
            "compact preview. The result_target must be a Garden artifact with "
            "artifact_type=dragonfly_grid_opendss_result_csv; arbitrary CSV paths "
            "are rejected."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "result", "read", "target"},
        timeout=20,
    )
    def read_opendss_result(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        result_target: Annotated[dict[str, Any], Field(description="Registered OpenDSS CSV result artifact target.")],
        max_rows: Annotated[int, Field(description="Maximum preview rows to return.")] = 25,
    ) -> dict[str, Any]:
        """Read a registered OpenDSS result artifact."""
        from garden.dragonfly_grid.authoring import read_opendss_result as service

        return service(garden_root=garden_root, result_target=result_target, max_rows=max_rows)

    @mcp.tool(
        name="DF_Grid_Search_OpenDSS",
        description=(
            "Search Dragonfly Energy OpenDSS catalog identifiers for transformer "
            "properties, power lines, and wires. Returns compact catalog records "
            "for DF_Grid_Transformer and DF_Grid_Electrical_Connector inputs, "
            "plus matches, summary_view, and report."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "search", "catalog", "list"},
        timeout=20,
    )
    def search_opendss(
        keywords: Annotated[list[str] | None, Field(description="Optional keywords that must all appear in the catalog identifier.")] = None,
        catalogs: Annotated[list[str] | None, Field(description="Optional catalogs: transformer_properties, power_lines, wires.")] = None,
        limit: Annotated[int, Field(description="Maximum compact records to return.")] = 25,
    ) -> dict[str, Any]:
        """Search OpenDSS catalog identifiers."""
        from garden.dragonfly_grid.authoring import search_opendss as service

        return service(keywords=keywords, catalogs=catalogs, limit=limit)

    @mcp.tool(
        name="DF_Grid_Start_OpenDSS",
        description=(
            'Start or block an OpenDSS run from a feature GeoJSON target and scenario CSV target. '
            'Returns a blocked run ledger when OpenDSS is unavailable.'
        ),
        tags={"dragonfly", "electric-grid", "opendss", "run", "runtime", "target"},
        timeout=30,
    )
    def start_opendss(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the OpenDSS project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        autosize: Annotated[bool, Field(description="Whether to request OpenDSS network upgrade/autosizing when runtime is ready.")] = False,
    ) -> dict[str, Any]:
        """Start or block an OpenDSS run."""
        from garden.dragonfly_grid.runs import start_opendss as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            autosize=autosize,
        )

    @mcp.tool(
        name="DF_Grid_Start_REopt",
        description=(
            'Start or block a Dragonfly Electric Grid REopt post-processing run from feature '
            'GeoJSON and scenario CSV targets. When no local REopt service is configured, returns '
            'a blocked ledger with runtime_diagnostics.external_api_blocker.'
        ),
        tags={"dragonfly", "electric-grid", "reopt", "run", "runtime", "target"},
        timeout=30,
    )
    def start_reopt(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the REopt project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        urdb_label: Annotated[str, Field(description="URDB utility rate label passed to Dragonfly Energy REopt when runtime is ready.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        developer_key: Annotated[str | None, Field(description='Optional REopt developer key (redacted in reports).')] = None,
    ) -> dict[str, Any]:
        """Start or block a REopt run."""
        from garden.dragonfly_grid.runs import start_reopt as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            urdb_label=urdb_label,
            run_id=run_id,
            developer_key=developer_key,
        )

    @mcp.tool(
        name="DF_Grid_Start_RNM",
        description=(
            "Start or block a Dragonfly Electric Grid RNM run from a feature "
            "GeoJSON target and scenario CSV target. Under the local-service "
            "runtime policy, API-backed RNM-US submission returns a blocked run "
            "ledger with runtime_diagnostics.external_api_blocker and "
            "LB_Get_Runtime_Config as the next check."
        ),
        tags={"dragonfly", "electric-grid", "rnm", "run", "runtime", "target"},
        timeout=30,
    )
    def start_rnm(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the URBANopt/RNM project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        underground_ratio: Annotated[float, Field(description="RNM underground ratio passed to Dragonfly Energy when runtime is ready.")] = 0.9,
        lv_only: Annotated[bool, Field(description="Whether RNM should run low-voltage-only network generation.")] = True,
        nodes_per_building: Annotated[int, Field(description="RNM nodes per building.")] = 1,
    ) -> dict[str, Any]:
        """Start or block an RNM run."""
        from garden.dragonfly_grid.runs import start_rnm as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            underground_ratio=underground_ratio,
            lv_only=lv_only,
            nodes_per_building=nodes_per_building,
        )
