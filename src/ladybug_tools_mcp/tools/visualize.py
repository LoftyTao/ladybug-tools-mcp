"""visualize MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register visualize tools."""

    @mcp.tool(
        name="LB_Compose_Model_Analysis_Visualization_Set",
        description=(
            'Compose a Garden-backed model-context VisualizationSet target with an '
            'analysis-result VisualizationSet target for overlays such as Honeybee wireframe plus '
            'Radiance mesh results. This combines existing VisualizationSet targets.'
        ),
        tags={
            "visualization-set",
            "visualize",
            "edit",
            "overlay",
        },
        timeout=30,
    )
    def compose_model_analysis_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_context_target: Annotated[
            dict[str, Any],
            Field(description="VisualizationSet target for model context geometry such as Honeybee model wireframe."),
        ],
        analysis_visualization_set_target: Annotated[
            dict[str, Any],
            Field(description="VisualizationSet target for the analysis/result layer."),
        ],
        name: Annotated[
            str,
            Field(description="Output VisualizationSet identifier and artifact name."),
        ] = "model_analysis_overlay",
        units: Annotated[
            str | None,
            Field(description="Optional output units. If omitted, input units must match."),
        ] = None,
        exclude_context_geometry_identifiers: Annotated[
            list[str] | None,
            Field(description="Context geometry layer identifiers to omit, defaulting to Sensor_Grids."),
        ] = None,
        conflict_strategy: Annotated[
            str,
            Field(description="Geometry identifier conflict strategy: error or rename."),
        ] = "rename",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. Set false for compact target handoff."),
        ] = True,
    ) -> dict[str, Any]:
        """Compose model context with an analysis VisualizationSet and save it."""
        from garden.visualize.honeybee import compose_model_analysis_visualization_set as service

        return service(
            garden_root=garden_root,
            model_context_target=model_context_target,
            analysis_visualization_set_target=analysis_visualization_set_target,
            name=name,
            units=units,
            exclude_context_geometry_identifiers=exclude_context_geometry_identifiers,
            conflict_strategy=conflict_strategy,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Compose_Visualization_Sets",
        description=(
            'Compose multiple Ladybug Display VisualizationSets into one scene from '
            'visualization_set dictionaries or Garden-backed visualization_set_targets. Pass '
            'garden_root and visualization_set_targets with return_visualization_set=false to '
            'persist a compact visualization_set_target for LB_Set_To_HTML, LB_Set_To_SVG, or '
            'LB_Set_To_VTKJS. Target dicts use target_type=visualization_set. For model and room '
            'preview overlays, set conflict_strategy=rename because wireframe identifiers often '
            'repeat. This tool composes display geometry.'
        ),
        tags={
            "visualization-set",
            "visualize",
            "edit",
            "compose",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def compose_visualization_sets(
        visualization_sets: Annotated[
            list[dict[str, Any]] | None,
            Field(description=(
                'VisualizationSet dictionaries to combine into one VisualizationSet. Use '
                'visualization_set_targets for compact Garden-backed composition.'
            )),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        visualization_set_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description=(
                'Garden-backed visualization_set targets from upstream visualize tools. Use '
                'target_type=visualization_set.'
            )),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional composed VisualizationSet identifier and display name."
            ),
        ] = None,
        units: Annotated[
            str | None,
            Field(
                description="Optional output units. If omitted, explicit input units must match; blank/missing units adopt the first explicit unit."
            ),
        ] = None,
        check_duplicate_geometry_ids: Annotated[
            bool, Field(description="Whether to check geometry identifier conflicts.")
        ] = True,
        conflict_strategy: Annotated[
            str,
            Field(
                description="Geometry identifier conflict strategy: error or rename. Use rename for model + room preview overlays because wireframe identifiers often repeat."
            ),
        ] = "error",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to save and return a compact visualization_set_target for exporters."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Compose VisualizationSet dictionaries into one VisualizationSet."""
        from garden.visualize.honeybee import compose_visualization_sets as service

        return service(
            visualization_sets=visualization_sets,
            garden_root=garden_root,
            visualization_set_targets=visualization_set_targets,
            name=name,
            units=units,
            check_duplicate_geometry_ids=check_duplicate_geometry_ids,
            conflict_strategy=conflict_strategy,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Create_2D_Legend_Parameter",
        description=(
            'Create a Ladybug Display 2D legend parameter payload for VisualizationSet chart and '
            'model exports. Use the returned object_dict in visualization or chart tools when a '
            'custom legend is needed. Returns object_dict and summary_view.'
        ),
        tags={
            "visualization-set",
            "visualize",
            "author",
            "legend",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def create_2d_legend_parameter(
        title: Annotated[
            str | None, Field(description="Optional 2D legend title.")
        ] = None,
        segment_count: Annotated[
            int | None, Field(description="Optional legend segment count.")
        ] = None,
        decimal_count: Annotated[
            int | None, Field(description="Optional decimal count for legend labels.")
        ] = None,
        minimum: Annotated[
            float | None, Field(description="Optional legend minimum value.")
        ] = None,
        maximum: Annotated[
            float | None, Field(description="Optional legend maximum value.")
        ] = None,
        position_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional 2D position dict with originx and originy, such as 5% or 20px."
            ),
        ] = None,
        dimensions_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional 2D dimensions dict with segment_height, segment_width, and text_height, such as 24px."
            ),
        ] = None,
        orientation: Annotated[
            str, Field(description="Legend orientation: vertical or horizontal.")
        ] = "vertical",
        color_set: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional Ladybug colorset name or dict with name/colors."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a 2D legend parameter dict."""
        from garden.visualize.legend import create_2d_legend_parameter as service

        return service(
            title=title,
            segment_count=segment_count,
            decimal_count=decimal_count,
            minimum=minimum,
            maximum=maximum,
            position_2d=position_2d,
            dimensions_2d=dimensions_2d,
            orientation=orientation,
            color_set=color_set,
        )

    @mcp.tool(
        name="LB_Data_Collection_Hourly_Plot_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet hourly plot from one hourly Ladybug '
            'DataCollection using Ladybug HourlyPlot. Use this for hourly energy result data, '
            'schedules, weather, comfort, or other time-series data after an upstream tool '
            'returns a ladybug_data_collection target. Pass garden_root and '
            'data_collection_target with return_visualization_set=false to persist a compact '
            'visualization_set_target for exporters. This charts an existing DataCollection.'
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "hourly-plot",
        },
        timeout=60,
    )
    def data_collection_hourly_plot_to_visualization_set(
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Ladybug hourly DataCollection dictionary. Use '
                    'data_collection_target for compact Garden-backed workflows.'
                )
            ),
        ] = None,
        data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional ladybug_data_collection target returned by an upstream tool such as EP_Create_Schedule_Ruleset with garden_root and return_data=false.'
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="HourlyPlot VisualizationSet identifier and display name."),
        ] = "data_collection_hourly_plot",
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK HourlyPlot X dimension for each day/cell column. Defaults to 1."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK HourlyPlot Y dimension for each hour/cell row. Defaults to 4."
            ),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to pass visualization_set_target downstream without a large object handoff."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create an HourlyPlot VisualizationSet from a DataCollection."""
        from garden.visualize.datacollection import (
            data_collection_hourly_plot_to_visualization_set as service,
        )

        return service(
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            garden_root=garden_root,
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Data_Collection_Monthly_Chart_To_HTML",
        description=(
            'Create a Garden HTML artifact from one or more Ladybug DataCollections using Ladybug '
            'MonthlyChart. Use series items with data_collection_target from Garden-backed '
            'upstream tools for schedule, weather, comfort, energy result, daily, monthly, or '
            'monthly-per-hour comparisons. Each series item uses data_collection or '
            'data_collection_target and optional label. This exports a chart artifact.'
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "artifact",
            "monthly-chart",
        },
        timeout=90,
    )
    def data_collection_monthly_chart_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires exactly one of data_collection, a Ladybug DataCollection dict, or data_collection_target, a ladybug_data_collection Garden target; may include label for the legend."
            ),
        ],
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour."
            ),
        ] = "as_is",
        chart_title: Annotated[
            str | None,
            Field(description="Optional global title for the chart."),
        ] = None,
        y_axis_title: Annotated[
            str | None,
            Field(description="Optional Y-axis title for the chart."),
        ] = None,
        stack: Annotated[
            bool,
            Field(description="Whether cumulative series should be stacked by MonthlyChart."),
        ] = False,
        percentile: Annotated[
            float,
            Field(description="Percentile spread used by MonthlyChart for hourly data."),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(
                description="Whether month labels are replaced with time-of-day marks. Automatically enabled for monthly_per_hour and total_monthly_per_hour charts."
            ),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart X dimension for each month. Defaults to 10, or 50 for monthly_per_hour/total_monthly_per_hour charts."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart Y dimension for the chart height. Defaults to 40."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="MonthlyChart HTML artifact file name without extension."),
        ] = "data_collection_monthly_chart",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/visualization/datacollections/html",
    ) -> dict[str, Any]:
        """Export Ladybug DataCollections to a MonthlyChart HTML artifact."""
        from garden.visualize.datacollection import (
            data_collection_monthly_chart_to_html as service,
        )

        return service(
            garden_root=garden_root,
            series=series,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="LB_Data_Collection_Monthly_Chart_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet monthly chart from one or more Ladybug '
            'DataCollection targets such as EnergyPlus result or EPW weather data already saved '
            'in the Garden. Each series uses data_collection_target or direct data_collection '
            'plus optional label metadata. This charts existing DataCollections. Returns target, '
            'visualization_set_target, summary_view, persistence_receipt, and report for '
            'vtkjs/html export.'
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "monthly-chart",
        },
        timeout=60,
    )
    def data_collection_monthly_chart_to_visualization_set(
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires exactly one of data_collection or data_collection_target, not both. data_collection is a Ladybug DataCollection dict; data_collection_target is a ladybug_data_collection Garden target. May include label for the legend."
            ),
        ],
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, hourly, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour. Use monthly for monthly average lines and monthly_per_hour for monthly average by hour patterns."
            ),
        ] = "as_is",
        chart_title: Annotated[
            str | None,
            Field(description="Optional global title for the chart."),
        ] = None,
        y_axis_title: Annotated[
            str | None,
            Field(description="Optional Y-axis title for the chart."),
        ] = None,
        stack: Annotated[
            bool,
            Field(description="Whether cumulative series should be stacked by MonthlyChart."),
        ] = False,
        percentile: Annotated[
            float,
            Field(description="Percentile spread used by MonthlyChart for hourly data."),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(
                description="Whether month labels are replaced with time-of-day marks. Automatically enabled for monthly_per_hour and total_monthly_per_hour charts."
            ),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart X dimension for each month. Defaults to 10, or 50 for monthly_per_hour/total_monthly_per_hour charts."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional Ladybug SDK MonthlyChart Y dimension for the chart height. Defaults to 40."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="MonthlyChart VisualizationSet identifier and display name."),
        ] = "data_collection_monthly_chart",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to pass visualization_set_target downstream without a large object handoff."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a MonthlyChart VisualizationSet from DataCollections."""
        from garden.visualize.datacollection import (
            data_collection_monthly_chart_to_visualization_set as service,
        )

        return service(
            series=series,
            garden_root=garden_root,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            x_dim=x_dim,
            y_dim=y_dim,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Data_Collection_To_File",
        description=(
            'Export one Ladybug DataCollection to a Garden artifact using Ladybug SDK native '
            'collections_to_json or collections_to_csv. Use this for result dump/export workflows '
            'after energyplus result, schedule, or weather tools return a ladybug_data_collection '
            "target. Pass garden_root, data_collection_target, and file_format ('json' or 'csv'). "
            'Writes a data artifact.'
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "artifact",
            "export",
        },
        timeout=60,
    )
    def data_collection_to_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        file_format: Annotated[
            str,
            Field(
                description="Required native SDK export format: json uses ladybug.datautil.collections_to_json; csv uses collections_to_csv. Set csv when the user asks for a spreadsheet/table-friendly file."
            ),
        ],
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Ladybug DataCollection dictionary. Use data_collection_target to '
                    'reference persisted DataCollections directly.'
                )
            ),
        ] = None,
        data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ladybug_data_collection target returned by an upstream Garden-backed tool. Preferred for token-saving export workflows."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="DataCollection artifact file name without extension."),
        ] = "data_collection",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/data_collections",
    ) -> dict[str, Any]:
        """Export a Ladybug DataCollection to a native SDK JSON or CSV artifact."""
        from garden.data_collection import export_data_collection_file as service

        return service(
            garden_root=garden_root,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            file_format=file_format,
            name=name,
            output_subdir=output_subdir,
            source={"producer": 'LB_Data_Collection_To_File'},
        )

    @mcp.tool(
        name="LB_Edit_2D_Legend_Parameter",
        description=(
            'Edit a Ladybug Display 2D legend parameter payload for VisualizationSet chart and '
            'model exports. Pass object_dict from LB_Create_2D_Legend_Parameter or an existing '
            'legend dict. Edits display settings only. Returns object_dict and summary_view.'
        ),
        tags={
            "visualization-set",
            "visualize",
            "author",
            "legend",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def edit_2d_legend_parameter(
        legend_parameter: Annotated[
            dict[str, Any],
            Field(
                description='2D LegendParameters dictionary returned by LB_Create_2D_Legend_Parameter.'
            ),
        ],
        title: Annotated[
            str | None, Field(description="Optional updated legend title.")
        ] = None,
        segment_count: Annotated[
            int | None, Field(description="Optional updated legend segment count.")
        ] = None,
        decimal_count: Annotated[
            int | None, Field(description="Optional updated decimal count.")
        ] = None,
        minimum: Annotated[
            float | None, Field(description="Optional updated legend minimum value.")
        ] = None,
        maximum: Annotated[
            float | None, Field(description="Optional updated legend maximum value.")
        ] = None,
        position_2d: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional updated 2D position dict with originx and originy."
            ),
        ] = None,
        dimensions_2d: Annotated[
            dict[str, Any] | None,
            Field(description="Optional updated 2D dimensions dict."),
        ] = None,
        orientation: Annotated[
            str | None,
            Field(description="Optional updated orientation: vertical or horizontal."),
        ] = None,
        color_set: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional updated Ladybug colorset name or dict with name/colors."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a 2D legend parameter dict."""
        from garden.visualize.legend import edit_2d_legend_parameter as service

        return service(
            legend_parameter=legend_parameter,
            title=title,
            segment_count=segment_count,
            decimal_count=decimal_count,
            minimum=minimum,
            maximum=maximum,
            position_2d=position_2d,
            dimensions_2d=dimensions_2d,
            orientation=orientation,
            color_set=color_set,
        )

    @mcp.tool(
        name="LB_Honeybee_Face_To_Visualization_Set",
        description=(
            'Visualize one Honeybee Face target as a Ladybug Display VisualizationSet. Use this '
            'read-only preview after object search finds the face target. For HTML/SVG/vtk.js '
            'export paths, set return_visualization_set=false so the tool saves a compact '
            'visualization_set_target for exporters. This previews existing Honeybee geometry.'
        ),
        tags={
            "honeybee",
            "face",
            "visualize",
            "visualization-set",
            "preview",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def honeybee_face_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        target: Annotated[
            dict[str, Any], Field(description="Honeybee Face typed target to convert into a VisualizationSet preview.")
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target. Defaults to target model or Garden base model."
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Face color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include a face wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only face wireframe visualization geometry."
            ),
        ] = False,
        include_sub_faces: Annotated[
            bool,
            Field(
                description="Whether face wireframe should include apertures and doors."
            ),
        ] = True,
        include_shades: Annotated[
            bool, Field(description="Whether face wireframe should include shades.")
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false to save and return a compact visualization_set_target."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Build a VisualizationSet from a Garden Honeybee Face typed target."""
        from garden.visualize.honeybee import (
            honeybee_face_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            wireframe_only=wireframe_only,
            include_sub_faces=include_sub_faces,
            include_shades=include_shades,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Honeybee_Model_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet from a Honeybee model in a Garden. '
            'color_by accepts type, boundary_condition, or none; use type for simple model '
            'previews. For HTML/SVG/vtk.js export paths, set return_visualization_set=false so '
            'the tool saves a compact visualization_set_target for exporters. This previews model '
            'geometry and attributes.'
        ),
        tags={
            "honeybee",
            "model",
            "preview",
            "visualize",
            "visualization-set",
        },
        timeout=30,
    )
    def honeybee_model_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Honeybee model target with target_type=honeybee_model. Defaults to '
                    'the Garden base model.'
                )
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Model color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include the model wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only wireframe visualization geometry."
            ),
        ] = False,
        use_mesh: Annotated[
            bool,
            Field(
                description="Whether colored model geometry should be DisplayMesh3D instead of DisplayFace3D."
            ),
        ] = False,
        hide_color_by: Annotated[
            bool,
            Field(
                description="Whether the color-by geometry layer should be hidden by default."
            ),
        ] = False,
        room_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional RoomAttribute specs for property-colored room AnalysisGeometry. Each spec supports name, attrs, color, text, and legend_parameter."
            ),
        ] = None,
        face_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional FaceAttribute specs for property-colored face AnalysisGeometry. Each spec supports name, attrs, color, text, legend_parameter, face_types, and boundary_conditions."
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description='Return the full VisualizationSet dict. Set false to save a compact Garden visualization_set_target for HTML, SVG, or vtk.js export.'
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from a Garden Honeybee model."""
        from garden.visualize.honeybee import (
            honeybee_model_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            wireframe_only=wireframe_only,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            room_attributes=room_attributes,
            face_attributes=face_attributes,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Honeybee_Room_To_Visualization_Set",
        description=(
            'Visualize one Honeybee Room target as a Ladybug Display VisualizationSet. color_by '
            'accepts type, boundary_condition, or none; use type for simple room previews. Use '
            'this read-only preview after object search finds the room target. For '
            'HTML/SVG/vtk.js export paths, set return_visualization_set=false so the tool saves a '
            'compact visualization_set_target for exporters. This previews existing room '
            'geometry.'
        ),
        tags={
            "honeybee",
            "preview",
            "room",
            "visualize",
            "visualization-set",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def honeybee_room_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        target: Annotated[
            dict[str, Any], Field(description='Honeybee Room typed target from object search or edit output.')
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the target model or Garden base model."
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Room color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include a room wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only room wireframe visualization geometry."
            ),
        ] = False,
        include_sub_faces: Annotated[
            bool,
            Field(
                description="Whether room wireframe should include apertures and doors."
            ),
        ] = True,
        include_shades: Annotated[
            bool, Field(description="Whether room wireframe should include shades.")
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false to save a compact Garden visualization_set_target for export tools."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Build a VisualizationSet from a Garden Honeybee Room typed target."""
        from garden.visualize.honeybee import (
            honeybee_room_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            wireframe_only=wireframe_only,
            include_sub_faces=include_sub_faces,
            include_shades=include_shades,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Psychrometric_Chart_To_Visualization_Set",
        description=(
            'Create a Ladybug PsychrometricChart VisualizationSet from two Garden '
            'ladybug_data_collection targets: temperature in C and relative humidity in %. '
            'Optional strategy_layers overlay aligned comfort result targets such as UTCI, '
            'Adaptive, or PMV on the same psychrometric chart. Each layer is a dictionary with '
            'data_collection_target, optional label, and optional LegendParameters dictionary. '
            'The chart uses the SDK-native psychrometric_chart_to_vis_set path, persists a '
            'compact visualization_set target, and returns summary_view plus a Garden '
            'persistence_receipt. Set return_visualization_set=false to omit the full '
            'VisualizationSet body before passing the target to LB_Set_To_HTML, LB_Set_To_SVG, or '
            'LB_Set_To_VTKJS.'
        ),
        tags={
            "ladybug",
            "psychrometric-chart",
            "thermal-comfort",
            "strategy",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def psychrometric_chart_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        temperature_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for dry-bulb temperature in C."),
        ],
        relative_humidity_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for relative humidity in percent."),
        ],
        strategy_layers: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional aligned comfort strategy layers. Each item must include data_collection_target and may include label and legend_parameter."),
        ] = None,
        average_pressure: Annotated[
            float,
            Field(description="Average air pressure in Pa; default 101325."),
        ] = 101325,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SDK LegendParameters dictionary for the chart hour-frequency mesh."),
        ] = None,
        base_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional chart base point as {x, y} or [x, y]."),
        ] = None,
        x_dim: Annotated[
            float,
            Field(description="SDK chart X scale per temperature degree; default 1."),
        ] = 1,
        y_dim: Annotated[
            float,
            Field(description="SDK chart Y scale per humidity-ratio unit; default 1500."),
        ] = 1500,
        min_temperature: Annotated[
            float,
            Field(description="Chart minimum temperature in C, or F when use_ip=true; default -20."),
        ] = -20,
        max_temperature: Annotated[
            float,
            Field(description="Chart maximum temperature in C, or F when use_ip=true; default 50."),
        ] = 50,
        max_humidity_ratio: Annotated[
            float,
            Field(description="Chart maximum humidity ratio in kg water/kg dry air; minimum 0.005."),
        ] = 0.03,
        use_ip: Annotated[
            bool,
            Field(description="Plot temperature in Fahrenheit instead of Celsius; default false."),
        ] = False,
        z: Annotated[
            float,
            Field(description="Z coordinate for the chart geometry; default 0."),
        ] = 0,
        plot_wet_bulb: Annotated[
            bool,
            Field(description="Plot constant wet-bulb lines instead of enthalpy lines; default false."),
        ] = False,
        name: Annotated[
            str,
            Field(description="Persisted VisualizationSet identifier and display name."),
        ] = "psychrometric_chart",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet body in addition to its persisted target; default true."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Garden-backed psychrometric chart VisualizationSet."""
        from garden.visualize.psychrometric_chart import (
            psychrometric_chart_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            temperature_target=temperature_target,
            relative_humidity_target=relative_humidity_target,
            strategy_layers=strategy_layers,
            average_pressure=average_pressure,
            legend_parameter=legend_parameter,
            base_point=base_point,
            x_dim=x_dim,
            y_dim=y_dim,
            min_temperature=min_temperature,
            max_temperature=max_temperature,
            max_humidity_ratio=max_humidity_ratio,
            use_ip=use_ip,
            z=z,
            plot_wet_bulb=plot_wet_bulb,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Sky_Matrix_To_Radiation_Dome_Visualization_Set",
        description=(
            'Create a cumulative Ladybug Radiance Radiation Dome VisualizationSet from a Garden '
            'sky_matrix target. This visualizes existing sky-matrix values as a dome for '
            'display/export.'
        ),
        tags={
            "radiation",
            "radiance",
            "sky",
            "visualize",
            "visualization-set",
        },
        timeout=120,
    )
    def sky_matrix_to_radiation_dome_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        sky_matrix_target: Annotated[
            dict[str, Any],
            Field(description='Existing Garden sky_matrix target returned by RAD_Create_Sky_Matrix.'),
        ],
        azimuth_count: Annotated[
            int,
            Field(description="Number of azimuth subdivisions for the dome mesh."),
        ] = 72,
        altitude_count: Annotated[
            int,
            Field(description="Number of altitude subdivisions for the dome mesh."),
        ] = 18,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameters dictionary."),
        ] = None,
        plot_irradiance: Annotated[
            bool,
            Field(description="When true, plot irradiance values; when false, plot radiation values."),
        ] = False,
        radius: Annotated[
            float,
            Field(description="Radiation dome radius."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional center point as {x,y,z} or [x,y,z]."),
        ] = None,
        projection: Annotated[
            str | None,
            Field(description="Optional 2D projection: Orthographic or Stereographic."),
        ] = None,
        show_components: Annotated[
            bool,
            Field(description="Show total, direct, and diffuse component domes."),
        ] = False,
        include_title: Annotated[
            bool,
            Field(description="Include the generated dome title text."),
        ] = True,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "radiation_dome",
        return_visualization_set: Annotated[
            bool,
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false with "
                    "garden_root to save and return a compact visualization_set_target."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a cumulative RadiationDome VisualizationSet."""
        from garden.visualize.sky import (
            sky_matrix_to_radiation_dome_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            sky_matrix_target=sky_matrix_target,
            azimuth_count=azimuth_count,
            altitude_count=altitude_count,
            legend_parameter=legend_parameter,
            plot_irradiance=plot_irradiance,
            radius=radius,
            center_point=center_point,
            projection=projection,
            show_components=show_components,
            include_title=include_title,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Sky_Matrix_To_Skydome_Visualization_Set",
        description=(
            'Create a Ladybug Display Sky Dome VisualizationSet from a Garden sky_matrix target. '
            'Use this to compose cumulative sky radiation context with model, sunpath, or '
            'analysis VisualizationSets. This visualizes existing sky-matrix data.'
        ),
        tags={
            "radiation",
            "radiance",
            "sky",
            "visualize",
            "visualization-set",
        },
        timeout=120,
    )
    def sky_matrix_to_skydome_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        sky_matrix_target: Annotated[
            dict[str, Any],
            Field(description='Existing Garden sky_matrix target returned by RAD_Create_Sky_Matrix.'),
        ],
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameters dictionary."),
        ] = None,
        plot_irradiance: Annotated[
            bool,
            Field(description="When true, plot irradiance values; when false, plot radiation values."),
        ] = False,
        radius: Annotated[
            float,
            Field(description="Sky dome radius."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional center point as {x,y,z} or [x,y,z]."),
        ] = None,
        projection: Annotated[
            str | None,
            Field(description="Optional 2D projection: Orthographic or Stereographic."),
        ] = None,
        show_components: Annotated[
            bool,
            Field(description="Show total, direct, and diffuse component domes."),
        ] = False,
        include_title: Annotated[
            bool,
            Field(description="Include the generated dome title text."),
        ] = True,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "sky_dome",
        return_visualization_set: Annotated[
            bool,
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false with "
                    "garden_root to save and return a compact visualization_set_target."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a SkyDome VisualizationSet from a SkyMatrix target."""
        from garden.visualize.sky import sky_matrix_to_skydome_visualization_set as service

        return service(
            garden_root=garden_root,
            sky_matrix_target=sky_matrix_target,
            legend_parameter=legend_parameter,
            plot_irradiance=plot_irradiance,
            radius=radius,
            center_point=center_point,
            projection=projection,
            show_components=show_components,
            include_title=include_title,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Sunpath_To_Visualization_Set",
        description=(
            'Create a Ladybug Display Sunpath VisualizationSet from a Location, Garden '
            'weather_file target, or Garden-relative EPW path. Use this for solar-analysis scenes '
            'that compose sunpath geometry with model or analysis VisualizationSets. This creates '
            'display geometry only.'
        ),
        tags={
            "sunpath",
            "weather",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def sunpath_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        location: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Ladybug Location dictionary. Provide one of "
                    "location, weather_target, or epw_path."
                )
            ),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Garden weather_file target. Provide one of "
                    "location, weather_target, or epw_path."
                )
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative EPW path. Provide one of "
                    "location, weather_target, or epw_path."
                )
            ),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year for displayed sun positions."),
        ] = None,
        radius: Annotated[
            float,
            Field(description="Sunpath radius."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional center point as {x,y,z} or [x,y,z]."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Draw hour labels using solar time."),
        ] = False,
        daily: Annotated[
            bool,
            Field(description="Draw only daily arcs for provided hoys."),
        ] = False,
        projection: Annotated[
            str | None,
            Field(description="Optional 2D projection: Orthographic or Stereographic."),
        ] = None,
        sun_spheres: Annotated[
            bool,
            Field(description="Render sun positions as spheres instead of points."),
        ] = False,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "sunpath",
        return_visualization_set: Annotated[
            bool,
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false with "
                    "garden_root to save and return a compact visualization_set_target."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Sunpath VisualizationSet."""
        from garden.visualize.sky import sunpath_to_visualization_set as service

        return service(
            garden_root=garden_root,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            north_angle=north_angle,
            hoys=hoys,
            radius=radius,
            center_point=center_point,
            solar_time=solar_time,
            daily=daily,
            projection=projection,
            sun_spheres=sun_spheres,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Set_To_HTML",
        description=(
            'Export a Ladybug Display VisualizationSet to a standalone interactive HTML page '
            'artifact inside a Garden and record it in garden.json artifacts. Use this when the '
            'user asks for an HTML page, report page, or browser-openable preview file. Pass '
            'visualization_set_target from an upstream visualize tool. For Web 3D geometry '
            'packages, vtk.js assets, FastMCP App viewer assets, reusable geometry assets, or '
            'vtk.js packages, use LB_Set_To_VTKJS.'
        ),
        tags={
            "visualization-set",
            "export",
            "artifact",
        },
        timeout=60,
    )
    def visualization_set_to_html(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct VisualizationSet dictionary from a visualize tool. Prefer visualization_set_target for compact Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with return_visualization_set=false."
            ),
        ] = None,
        name: Annotated[
            str, Field(description="HTML artifact file name without extension.")
        ] = "visualization_set",
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/html",
        open: Annotated[
            bool, Field(description="Whether to open the HTML artifact after export.")
        ] = False,
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden HTML artifact."""
        from garden.visualize.artifacts import visualization_set_to_html as service

        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
            open=open,
        )

    @mcp.tool(
        name="LB_Set_To_SVG",
        description=(
            'Export a Ladybug Display VisualizationSet to an SVG artifact inside a Garden and '
            'record it in garden.json artifacts. Pass visualization_set_target from an upstream '
            'visualize tool. This writes a static SVG export.'
        ),
        tags={
            "visualization-set",
            "export",
            "artifact",
        },
        timeout=60,
    )
    def visualization_set_to_svg(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct VisualizationSet dictionary from a visualize or compose tool. Prefer visualization_set_target for compact Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with return_visualization_set=false."
            ),
        ] = None,
        width: Annotated[int, Field(description="SVG canvas width in pixels.")] = 1600,
        height: Annotated[int, Field(description="SVG canvas height in pixels.")] = 900,
        view: Annotated[
            str,
            Field(
                description="Projection view: Top, Left, Right, Front, Back, NE, NW, SE, or SW."
            ),
        ] = "Top",
        interactive: Annotated[
            bool, Field(description="Whether to preserve SVG hover interactivity.")
        ] = False,
        render_2d_legend: Annotated[
            bool, Field(description="Whether to render 2D legends in the SVG.")
        ] = True,
        render_3d_legend: Annotated[
            bool, Field(description="Whether to render 3D legends in the SVG.")
        ] = False,
        name: Annotated[
            str, Field(description="SVG artifact file name without extension.")
        ] = "visualization_set",
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/svg",
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden SVG artifact."""
        from garden.visualize.artifacts import visualization_set_to_svg as service

        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            width=width,
            height=height,
            view=view,
            interactive=interactive,
            render_2d_legend=render_2d_legend,
            render_3d_legend=render_3d_legend,
            name=name,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="LB_Set_To_VTKJS",
        description=(
            'Export a Ladybug Display VisualizationSet to a persistent .vtkjs artifact inside a '
            'Garden and record it in garden.json artifacts. Use this when the user asks for a '
            'saved vtk.js or Web 3D asset for a FastMCP App viewer, vtk.js, WebGL, or reusable '
            'geometry workflows. Pass visualization_set_target from an upstream visualize tool.'
        ),
        tags={
            "visualization-set",
            "vtkjs",
            "export",
            "artifact",
        },
        timeout=60,
    )
    def visualization_set_to_vtkjs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct VisualizationSet dictionary from a visualize tool. Prefer visualization_set_target for compact Garden workflows."
            ),
        ] = None,
        visualization_set_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional visualization_set target returned by an upstream visualize tool with return_visualization_set=false."
            ),
        ] = None,
        name: Annotated[
            str, Field(description="vtkjs artifact file name without extension.")
        ] = "visualization_set",
        output_subdir: Annotated[
            str, Field(description="Garden-relative artifact output directory.")
        ] = "artifacts/visualization/vtkjs",
    ) -> dict[str, Any]:
        """Export a VisualizationSet to a Garden vtkjs artifact."""
        from garden.visualize.artifacts import visualization_set_to_vtkjs as service

        return service(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="LB_Windrose_To_Visualization_Set",
        description=(
            'Create a Ladybug WindRose from aligned hourly wind-direction and analysis '
            'DataCollections, returning compact directional frequency statistics and a native '
            'VisualizationSet. The analysis collection is usually wind_speed, but other hourly '
            'numeric data can also be binned by direction. Use Garden targets and set '
            'return_visualization_set=false to persist a visualization_set target for '
            'LB_Set_To_HTML, LB_Set_To_SVG, or LB_Set_To_VTKJS. For wind speed, calm_threshold '
            'marks values at or below the threshold as calm and reports their count and '
            'percentage. Use EP_Read_Weather_File_Data first to extract collections from EPW '
            'files. An optional analysis_period filters both inputs before calculating the rose.'
        ),
        tags={
            "ladybug",
            "wind",
            "windrose",
            "weather",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def windrose_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(
                description="Garden root path containing garden.json, required for Garden DataCollection targets and persisted VisualizationSets."
            ),
        ],
        direction_data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct hourly Ladybug DataCollection dictionary of wind directions in degrees. Provide exactly one direction input with direction_data_collection_target."
            ),
        ] = None,
        direction_data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Garden ladybug_data_collection target for hourly wind directions. Preferred over a full dictionary."
            ),
        ] = None,
        analysis_data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct hourly Ladybug DataCollection dictionary to bin by direction, usually wind speed. Provide exactly one analysis input with analysis_data_collection_target."
            ),
        ] = None,
        analysis_data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Garden ladybug_data_collection target to bin by direction, usually the wind_speed target returned by EP_Read_Weather_File_Data. Preferred over a full dictionary."
            ),
        ] = None,
        direction_count: Annotated[
            int,
            Field(description="Number of directional sectors; must be at least 3. Defaults to 36."),
        ] = 36,
        calm_threshold: Annotated[
            float,
            Field(
                description="Wind-speed values at or below this threshold are counted as calm. Applies only when the analysis data type is Speed; defaults to the SDK threshold 1e-10 m/s."
            ),
        ] = 1e-10,
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dictionary or string applied to both input collections before binning, for example '7/1 to 7/31 between 0 and 23 @1'."
            ),
        ] = None,
        north: Annotated[
            float,
            Field(description="Counterclockwise north orientation in degrees; defaults to 0."),
        ] = 0.0,
        show_zeros: Annotated[
            bool,
            Field(description="Show calm wind as the central zero-value ring when analysis data is wind speed."),
        ] = False,
        frequency_labels: Annotated[
            bool,
            Field(description="Include frequency labels in the native VisualizationSet."),
        ] = True,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "wind_rose",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet body. Set false to save and return visualization_set_target for existing exporters."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create WindRose statistics and a VisualizationSet."""
        from garden.visualize.windrose import windrose_to_visualization_set as service

        return service(
            garden_root=garden_root,
            direction_data_collection=direction_data_collection,
            direction_data_collection_target=direction_data_collection_target,
            analysis_data_collection=analysis_data_collection,
            analysis_data_collection_target=analysis_data_collection_target,
            direction_count=direction_count,
            calm_threshold=calm_threshold,
            analysis_period=analysis_period,
            north=north,
            show_zeros=show_zeros,
            frequency_labels=frequency_labels,
            name=name,
            return_visualization_set=return_visualization_set,
        )
