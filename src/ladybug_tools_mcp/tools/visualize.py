"""Consolidated MCP tools for Ladybug/Honeybee visualization and export."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    ArtifactTargetRef,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    DataCollectionTargetRef,
    MutationResultModel,
    SkyTargetRef,
    WeatherTargetRef,
    dump_input,
    dump_target,
    dump_targets,
    validate_output,
)
from garden.data_collection import export_data_collection_file
from garden.run_energy.results import (
    _data_collections,
    _monthly_chart_series,
    _sql_result,
    energy_result_hourly_plot_to_html,
    energy_result_monthly_chart_to_html,
)
from garden.solar_studies import run_solar_geometry_study
from garden.visualize.artifacts import (
    coerce_legend_parameter_dict,
    export_visualization_set,
    visualization_set_to_html,
)
from garden.visualize.datacollection import (
    data_collection_hourly_plot_to_html,
    data_collection_hourly_plot_to_visualization_set,
    data_collection_monthly_chart_to_html,
    data_collection_monthly_chart_to_visualization_set,
)
from garden.visualize.honeybee import (
    compose_model_analysis_visualization_set,
    compose_visualization_sets,
    honeybee_face_to_visualization_set,
    honeybee_model_to_visualization_set,
    honeybee_room_to_visualization_set,
)
from garden.visualize.psychrometric_chart import (
    adaptive_chart_to_visualization_set,
    psychrometric_chart_to_visualization_set,
)
from garden.visualize.sky import (
    compass_to_visualization_set,
    sky_matrix_to_radiation_dome_visualization_set,
    sky_matrix_to_radiation_rose_visualization_set,
    sky_matrix_to_skydome_visualization_set,
    sunpath_to_visualization_set,
    view_sphere_to_visualization_set,
    wind_profile_to_visualization_set,
)
from garden.visualize.windrose import windrose_to_visualization_set


def _require_garden_root(garden_root: str | None, context: str) -> str:
    if not garden_root:
        raise ValueError(f"garden_root is required for {context}.")
    return garden_root


def _coerce_strategy_layers(
    strategy_layers: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if strategy_layers is None:
        return None
    coerced_layers: list[dict[str, Any]] = []
    for layer in strategy_layers:
        if isinstance(layer, dict) and layer.get("legend_parameter") is not None:
            updated = dict(layer)
            updated["legend_parameter"] = coerce_legend_parameter_dict(
                layer.get("legend_parameter")
            )
            coerced_layers.append(updated)
        else:
            coerced_layers.append(layer)
    return coerced_layers


def _extract_energy_hourly_collection(
    *,
    garden_root: str,
    energy_run_target: dict[str, Any] | None,
    run_id: str | None,
    output_name: str,
    collection_index: int,
    run_period_index: int | None,
) -> dict[str, Any]:
    garden_root_path = Path(garden_root).expanduser().resolve()
    _run_id, _sql_path, sql, _record = _sql_result(
        garden_root=garden_root_path,
        run_target=energy_run_target,
        run_id=run_id,
    )
    collections = _data_collections(sql, output_name, run_period_index)
    if not collections:
        raise ValueError(f"No DataCollections found for output_name={output_name!r}.")
    if collection_index < 0 or collection_index >= len(collections):
        raise ValueError(
            f"collection_index {collection_index} is outside the returned DataCollection range (0..{len(collections) - 1})."
        )
    return collections[collection_index].to_dict()


def _extract_energy_monthly_series(
    *,
    garden_root: str,
    energy_run_target: dict[str, Any] | None,
    run_id: str | None,
    series: list[dict[str, Any]],
    time_interval: str,
) -> list[dict[str, Any]]:
    garden_root_path = Path(garden_root).expanduser().resolve()
    _run_id, _sql_path, sql, _record = _sql_result(
        garden_root=garden_root_path,
        run_target=energy_run_target,
        run_id=run_id,
    )
    collections, summaries = _monthly_chart_series(
        sql=sql,
        series=series,
        time_interval=time_interval,
    )
    return [
        {
            "data_collection": collection.to_dict(),
            "label": summary.get("label"),
        }
        for collection, summary in zip(collections, summaries)
    ]


def register(mcp: FastMCP) -> None:
    """Register consolidated visualization and export MCP tools."""

    @mcp.tool(
        name="LB_Honeybee_To_Visualization_Set",
        tags={"ladybug", "honeybee", "visualization", "visualization-set", "display", "target"},
        timeout=45,
    )
    def LB_Honeybee_To_Visualization_Set(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Honeybee room or face target (omit for full model)."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Target Honeybee Model reference (defaults to active model)."),
        ] = None,
        color_by: Annotated[
            Literal["type", "boundary_condition", "none", "None"] | None,
            Field(description="Face coloring mode: 'type', 'boundary_condition', or 'none'."),
        ] = "type",
        include_wireframe: Annotated[
            bool,
            Field(description="Include wireframe geometry in the VisualizationSet."),
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(description="Output only wireframe geometry without surface coloring."),
        ] = False,
        use_mesh: Annotated[
            bool,
            Field(description="Represent faces as triangulated meshes instead of Face3D."),
        ] = False,
        hide_color_by: Annotated[
            bool,
            Field(description="Hide the color_by geometry layer by default."),
        ] = False,
        room_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Room attribute specs (name, color_by, etc.) to visualize on rooms."),
        ] = None,
        face_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Face attribute specs to visualize on faces."),
        ] = None,
        include_sub_faces: Annotated[
            bool,
            Field(description="Include apertures and doors when visualizing a room or face."),
        ] = True,
        include_shades: Annotated[
            bool,
            Field(description="Include attached shades when visualizing a room or face."),
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Include the full VisualizationSet dictionary in the response."),
        ] = True,
    ) -> MutationResultModel:
        """Convert a Honeybee Model, Room, or Face to a VisualizationSet."""
        dumped_target = dump_target(target)
        dumped_model_target = dump_target(model_target)
        dumped_room_attrs = dump_input(room_attributes)
        dumped_face_attrs = dump_input(face_attributes)

        if dumped_target is None or dumped_target.get("object_type") == "model":
            return validate_output(
                MutationResultModel,
                honeybee_model_to_visualization_set(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                    color_by=color_by,
                    include_wireframe=include_wireframe,
                    wireframe_only=wireframe_only,
                    use_mesh=use_mesh,
                    hide_color_by=hide_color_by,
                    room_attributes=dumped_room_attrs,
                    face_attributes=dumped_face_attrs,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )
        object_type = dumped_target.get("object_type")
        if object_type == "room":
            return validate_output(
                MutationResultModel,
                honeybee_room_to_visualization_set(
                    garden_root=garden_root,
                    target=dumped_target,
                    model_target=dumped_model_target,
                    color_by=color_by,
                    include_wireframe=include_wireframe,
                    wireframe_only=wireframe_only,
                    include_sub_faces=include_sub_faces,
                    include_shades=include_shades,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )
        if object_type == "face":
            return validate_output(
                MutationResultModel,
                honeybee_face_to_visualization_set(
                    garden_root=garden_root,
                    target=dumped_target,
                    model_target=dumped_model_target,
                    color_by=color_by,
                    include_wireframe=include_wireframe,
                    wireframe_only=wireframe_only,
                    include_sub_faces=include_sub_faces,
                    include_shades=include_shades,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )
        raise ValueError(
            f"Unsupported Honeybee object_type in target: {object_type!r}. Expected 'room', 'face', or omit target for full model."
        )

    @mcp.tool(
        name="LB_Chart_To_Visualization_Set",
        description=(
            "Build HourlyPlot, MonthlyChart, PsychrometricChart, AdaptiveChart, or WindRose "
            "VisualizationSet or HTML. Use return_visualization_set=False for compact summary/target; "
            "use LB_Export_Visualization_Set for SVG/PNG/VTK/pixel sizing."
        ),
        tags={"ladybug", "visualization", "visualization-set", "chart", "hourly-plot", "monthly-chart", "psychrometric", "windrose", "html", "legend"},
        timeout=45,
    )
    def LB_Chart_To_Visualization_Set(
        chart_type: Annotated[
            Literal[
                "hourly_plot",
                "monthly_chart",
                "psychrometric_chart",
                "adaptive_chart",
                "windrose",
            ],
            Field(description="Chart type."),
        ],
        export_format: Annotated[
            Literal["visualization_set", "html"],
            Field(description="Output format."),
        ] = "visualization_set",
        garden_root: Annotated[
            Any,
            Field(description="Garden root path."),
        ] = None,
        legend_parameter: Annotated[
            Any,
            Field(description="LegendParameters overrides dict."),
        ] = None,
        x_dim: Annotated[
            Any,
            Field(description="Model X dimension."),
        ] = None,
        y_dim: Annotated[
            Any,
            Field(description="Model Y dimension."),
        ] = None,
        width: Annotated[
            Any,
            Field(description="Width px (see LB_Export_Visualization_Set)."),
        ] = None,
        height: Annotated[
            Any,
            Field(description="Height px (see LB_Export_Visualization_Set)."),
        ] = None,
        name: Annotated[
            Any,
            Field(description="Output name."),
        ] = None,
        output_subdir: Annotated[
            Any,
            Field(description="HTML subdir."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Return VisualizationSet JSON (False recommended)."),
        ] = True,
        energy_run_target: Annotated[
            Any,
            Field(description="SQL run target."),
        ] = None,
        run_id: Annotated[
            Any,
            Field(description="SQL run_id."),
        ] = None,
        output_name: Annotated[
            Any,
            Field(description="SQL output."),
        ] = None,
        collection_index: Annotated[
            int,
            Field(description="SQL index."),
        ] = 0,
        run_period_index: Annotated[
            Any,
            Field(description="Run period idx."),
        ] = None,
        data_collection: Annotated[
            Any,
            Field(description="DataCollection dict."),
        ] = None,
        data_collection_target: Annotated[
            Any,
            Field(description="DataCollection target."),
        ] = None,
        series: Annotated[
            Any,
            Field(description="Series list."),
        ] = None,
        time_interval: Annotated[
            str,
            Field(description="as_is, hourly, daily, monthly, total_*."),
        ] = "as_is",
        chart_title: Annotated[
            Any,
            Field(description="Chart title."),
        ] = None,
        y_axis_title: Annotated[
            Any,
            Field(description="Y-axis label."),
        ] = None,
        stack: Annotated[
            bool,
            Field(description="Stack series."),
        ] = False,
        percentile: Annotated[
            float,
            Field(description="Percentile 0-100."),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(description="Hour marks."),
        ] = False,
        temperature_target: Annotated[
            Any,
            Field(description="Air temp target."),
        ] = None,
        relative_humidity_target: Annotated[
            Any,
            Field(description="RH % target."),
        ] = None,
        strategy_layers: Annotated[
            Any,
            Field(description="Overlay specs."),
        ] = None,
        average_pressure: Annotated[
            float,
            Field(description="Pressure Pa."),
        ] = 101325,
        base_point: Annotated[
            Any,
            Field(description="Origin point."),
        ] = None,
        min_temperature: Annotated[
            float,
            Field(description="Min temp C."),
        ] = -20,
        max_temperature: Annotated[
            float,
            Field(description="Max temp C."),
        ] = 50,
        max_humidity_ratio: Annotated[
            float,
            Field(description="Max hum ratio."),
        ] = 0.03,
        use_ip: Annotated[
            bool,
            Field(description="IP units."),
        ] = False,
        z: Annotated[
            float,
            Field(description="Z elevation."),
        ] = 0,
        plot_wet_bulb: Annotated[
            bool,
            Field(description="Wet-bulb lines."),
        ] = False,
        direction_data_collection: Annotated[
            Any,
            Field(description="Wind dir dict."),
        ] = None,
        direction_data_collection_target: Annotated[
            Any,
            Field(description="Wind dir target."),
        ] = None,
        analysis_data_collection: Annotated[
            Any,
            Field(description="Petal dict."),
        ] = None,
        analysis_data_collection_target: Annotated[
            Any,
            Field(description="Petal target."),
        ] = None,
        direction_count: Annotated[
            int,
            Field(description="Bins >=3."),
        ] = 36,
        calm_threshold: Annotated[
            float,
            Field(description="Calm thresh."),
        ] = 1e-10,
        analysis_period: Annotated[
            Any,
            Field(description="AnalysisPeriod."),
        ] = None,
        north: Annotated[
            float,
            Field(description="North deg."),
        ] = 0.0,
        show_zeros: Annotated[
            bool,
            Field(description="Show zeros."),
        ] = False,
        frequency_labels: Annotated[
            bool,
            Field(description="Freq rings."),
        ] = True,
        z_dim: Annotated[
            float,
            Field(description="3D Z scale."),
        ] = 0.0,
        reverse_y: Annotated[
            bool,
            Field(description="Reverse Y."),
        ] = False,
        custom_hours: Annotated[
            Any,
            Field(description="Custom hours."),
        ] = None,
        y_axis_min: Annotated[
            Any,
            Field(description="Lower Y bound."),
        ] = None,
        y_axis_max: Annotated[
            Any,
            Field(description="Upper Y bound."),
        ] = None,
        comfort_polygon: Annotated[
            Any,
            Field(description="Polygon dict."),
        ] = None,
        include_passive_strategies: Annotated[
            bool,
            Field(description="Passive polygons."),
        ] = True,
        passive_strategy_parameters: Annotated[
            Any,
            Field(description="Strategy params."),
        ] = None,
        passive_strategies: Annotated[
            Any,
            Field(description="Strategy names."),
        ] = None,
        incident_irradiance_target: Annotated[
            Any,
            Field(description="Irradiance target."),
        ] = None,
        outdoor_temperature_target: Annotated[
            Any,
            Field(description="Outdoor target."),
        ] = None,
        operative_temperature_target: Annotated[
            Any,
            Field(description="Operative target."),
        ] = None,
        air_temperature_target: Annotated[
            Any,
            Field(description="Air temp target."),
        ] = None,
        mean_radiant_temperature_target: Annotated[
            Any,
            Field(description="MRT target."),
        ] = None,
        air_speed_target: Annotated[
            Any,
            Field(description="Air speed target."),
        ] = None,
        wind_speed_target: Annotated[
            Any,
            Field(description="Wind speed target."),
        ] = None,
        comfort_parameter: Annotated[
            Any,
            Field(description="PMV/AdaptiveParameter dict."),
        ] = None,
        min_prevailing: Annotated[
            float,
            Field(description="Min prevailing C."),
        ] = 10,
        max_prevailing: Annotated[
            float,
            Field(description="Max prevailing C."),
        ] = 33,
        min_operative: Annotated[
            float,
            Field(description="Min operative C."),
        ] = 14,
        max_operative: Annotated[
            float,
            Field(description="Max operative C."),
        ] = 40,
    ) -> ArtifactResultModel:
        """Build HourlyPlot, MonthlyChart, PsychrometricChart, AdaptiveChart, or WindRose VisualizationSet/HTML."""
        from garden.visualize._schemas import normalize_chart_inputs

        params = normalize_chart_inputs(
            {
                "chart_type": chart_type,
                "export_format": export_format,
                "garden_root": garden_root,
                "legend_parameter": legend_parameter,
                "x_dim": x_dim,
                "y_dim": y_dim,
                "width": width,
                "height": height,
                "name": name,
                "output_subdir": output_subdir,
                "return_visualization_set": return_visualization_set,
                "energy_run_target": energy_run_target,
                "run_id": run_id,
                "output_name": output_name,
                "collection_index": collection_index,
                "run_period_index": run_period_index,
                "data_collection": data_collection,
                "data_collection_target": data_collection_target,
                "series": series,
                "time_interval": time_interval,
                "chart_title": chart_title,
                "y_axis_title": y_axis_title,
                "stack": stack,
                "percentile": percentile,
                "time_marks": time_marks,
                "temperature_target": temperature_target,
                "relative_humidity_target": relative_humidity_target,
                "strategy_layers": strategy_layers,
                "average_pressure": average_pressure,
                "base_point": base_point,
                "min_temperature": min_temperature,
                "max_temperature": max_temperature,
                "max_humidity_ratio": max_humidity_ratio,
                "use_ip": use_ip,
                "z": z,
                "plot_wet_bulb": plot_wet_bulb,
                "direction_data_collection": direction_data_collection,
                "direction_data_collection_target": direction_data_collection_target,
                "analysis_data_collection": analysis_data_collection,
                "analysis_data_collection_target": analysis_data_collection_target,
                "direction_count": direction_count,
                "calm_threshold": calm_threshold,
                "analysis_period": analysis_period,
                "north": north,
                "show_zeros": show_zeros,
                "frequency_labels": frequency_labels,
                "z_dim": z_dim,
                "reverse_y": reverse_y,
                "custom_hours": custom_hours,
                "y_axis_min": y_axis_min,
                "y_axis_max": y_axis_max,
                "comfort_polygon": comfort_polygon,
                "include_passive_strategies": include_passive_strategies,
                "passive_strategy_parameters": passive_strategy_parameters,
                "passive_strategies": passive_strategies,
                "incident_irradiance_target": incident_irradiance_target,
                "outdoor_temperature_target": outdoor_temperature_target,
                "operative_temperature_target": operative_temperature_target,
                "air_temperature_target": air_temperature_target,
                "mean_radiant_temperature_target": mean_radiant_temperature_target,
                "air_speed_target": air_speed_target,
                "wind_speed_target": wind_speed_target,
                "comfort_parameter": comfort_parameter,
                "min_prevailing": min_prevailing,
                "max_prevailing": max_prevailing,
                "min_operative": min_operative,
                "max_operative": max_operative,
            }
        )
        pixel_width = params.pop("width", None)
        pixel_height = params.pop("height", None)

        def _finish(res: dict[str, Any]) -> ArtifactResultModel:
            if pixel_width is not None or pixel_height is not None:
                res.setdefault("summary_view", {})["export_dimensions_note"] = (
                    f"Chart geometry uses model units (x_dim/y_dim); passed pixel hints "
                    f"width={pixel_width}, height={pixel_height} apply when exporting via "
                    "LB_Export_Visualization_Set(export_format='svg'|'png', width=..., height=...)."
                )
            return validate_output(ArtifactResultModel, res)

        dumped_energy_run_target = params["energy_run_target"]
        dumped_dc_target = params["data_collection_target"]
        dumped_dc = params["data_collection"]
        dumped_series = params["series"]
        coerced_legend = coerce_legend_parameter_dict(params["legend_parameter"])
        chart_type = params["chart_type"]
        export_format = params["export_format"]
        garden_root = params["garden_root"]
        x_dim = params["x_dim"]
        y_dim = params["y_dim"]
        name = params["name"]
        output_subdir = params["output_subdir"]
        return_visualization_set = params["return_visualization_set"]
        run_id = params["run_id"]
        output_name = params["output_name"]
        collection_index = params["collection_index"]
        run_period_index = params["run_period_index"]
        time_interval = params["time_interval"]
        chart_title = params["chart_title"]
        y_axis_title = params["y_axis_title"]
        stack = params["stack"]
        percentile = params["percentile"]
        time_marks = params["time_marks"]
        z_dim = params["z_dim"]
        reverse_y = params["reverse_y"]
        custom_hours = params["custom_hours"]
        y_axis_min = params["y_axis_min"]
        y_axis_max = params["y_axis_max"]

        if chart_type == "hourly_plot":
            chart_name = name or (
                "energy_result_hourly_plot"
                if (dumped_energy_run_target is not None or run_id is not None or output_name is not None)
                else "data_collection_hourly_plot"
            )
            is_sql_input = (
                dumped_dc is None
                and dumped_dc_target is None
                and (dumped_energy_run_target is not None or run_id is not None or output_name is not None)
            )
            if is_sql_input:
                if not output_name:
                    raise ValueError(
                        "output_name is required for Energy SQL hourly_plot."
                    )
                root = _require_garden_root(garden_root, "Energy SQL hourly_plot")
                if (
                    export_format == "html"
                    and coerced_legend is None
                    and x_dim is None
                    and y_dim is None
                    and run_period_index is None
                ):
                    return _finish(
                        energy_result_hourly_plot_to_html(
                            garden_root=root,
                            run_target=dumped_energy_run_target,
                            run_id=run_id,
                            output_name=output_name,
                            collection_index=collection_index,
                            name=chart_name,
                            output_subdir=output_subdir or "artifacts/energy/results/html",
                        )
                    )
                dumped_dc = _extract_energy_hourly_collection(
                    garden_root=root,
                    energy_run_target=dumped_energy_run_target,
                    run_id=run_id,
                    output_name=output_name,
                    collection_index=collection_index,
                    run_period_index=run_period_index,
                )

            if export_format == "html":
                root = _require_garden_root(garden_root, "hourly_plot HTML export")
                return _finish(
                    data_collection_hourly_plot_to_html(
                        garden_root=root,
                        data_collection=dumped_dc,
                        data_collection_target=dumped_dc_target,
                        legend_parameter=coerced_legend,
                        x_dim=x_dim,
                        y_dim=y_dim,
                        z_dim=z_dim,
                        reverse_y=reverse_y,
                        custom_hours=custom_hours,
                        name=chart_name,
                        output_subdir=output_subdir or "artifacts/visualization/datacollections/html",
                    )
                )
            return _finish(
                data_collection_hourly_plot_to_visualization_set(
                    data_collection=dumped_dc,
                    data_collection_target=dumped_dc_target,
                    garden_root=garden_root,
                    legend_parameter=coerced_legend,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    z_dim=z_dim,
                    reverse_y=reverse_y,
                    custom_hours=custom_hours,
                    name=chart_name,
                    return_visualization_set=return_visualization_set,
                )
            )

        if chart_type == "monthly_chart":
            if not dumped_series:
                raise ValueError("series must include at least one entry for monthly_chart.")
            is_sql_series = (
                dumped_energy_run_target is not None
                or run_id is not None
                or any(
                    isinstance(item, dict)
                    and "output_name" in item
                    and "data_collection" not in item
                    and "data_collection_target" not in item
                    for item in dumped_series
                )
            )
            chart_name = name or (
                "energy_result_monthly_chart"
                if is_sql_series
                else "data_collection_monthly_chart"
            )
            effective_time_interval = time_interval
            resolved_series = dumped_series
            if is_sql_series:
                root = _require_garden_root(garden_root, "Energy SQL monthly_chart")
                if (
                    export_format == "html"
                    and coerced_legend is None
                    and x_dim is None
                    and y_dim is None
                ):
                    return _finish(
                        energy_result_monthly_chart_to_html(
                            garden_root=root,
                            series=dumped_series,
                            run_target=dumped_energy_run_target,
                            run_id=run_id,
                            time_interval=time_interval,
                            chart_title=chart_title,
                            y_axis_title=y_axis_title,
                            stack=stack,
                            percentile=percentile,
                            time_marks=time_marks,
                            name=chart_name,
                            output_subdir=output_subdir or "artifacts/energy/results/html",
                        )
                    )
                resolved_series = _extract_energy_monthly_series(
                    garden_root=root,
                    energy_run_target=dumped_energy_run_target,
                    run_id=run_id,
                    series=dumped_series,
                    time_interval=time_interval,
                )
                effective_time_interval = "as_is"

            if export_format == "html":
                root = _require_garden_root(garden_root, "monthly_chart HTML export")
                return _finish(
                    data_collection_monthly_chart_to_html(
                        garden_root=root,
                        series=resolved_series,
                        time_interval=effective_time_interval,
                        chart_title=chart_title,
                        y_axis_title=y_axis_title,
                        stack=stack,
                        percentile=percentile,
                        time_marks=time_marks,
                        y_axis_min=y_axis_min,
                        y_axis_max=y_axis_max,
                        legend_parameter=coerced_legend,
                        x_dim=x_dim,
                        y_dim=y_dim,
                        name=chart_name,
                        output_subdir=output_subdir or "artifacts/visualization/datacollections/html",
                    )
                )
            return _finish(
                data_collection_monthly_chart_to_visualization_set(
                    series=resolved_series,
                    garden_root=garden_root,
                    time_interval=effective_time_interval,
                    chart_title=chart_title,
                    y_axis_title=y_axis_title,
                    stack=stack,
                    percentile=percentile,
                    time_marks=time_marks,
                    y_axis_min=y_axis_min,
                    y_axis_max=y_axis_max,
                    legend_parameter=coerced_legend,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    name=chart_name,
                    return_visualization_set=return_visualization_set,
                )
            )

        if chart_type == "psychrometric_chart":
            root = _require_garden_root(garden_root, "psychrometric_chart")
            dumped_temp_target = params["temperature_target"]
            dumped_rh_target = params["relative_humidity_target"]
            if dumped_temp_target is None or dumped_rh_target is None:
                raise ValueError(
                    "temperature_target and relative_humidity_target are required for psychrometric_chart."
                )
            chart_name = name or "psychrometric_chart"
            res = psychrometric_chart_to_visualization_set(
                garden_root=root,
                temperature_target=dumped_temp_target,
                relative_humidity_target=dumped_rh_target,
                strategy_layers=_coerce_strategy_layers(params["strategy_layers"]),
                comfort_polygon=params["comfort_polygon"],
                include_passive_strategies=params["include_passive_strategies"],
                passive_strategy_parameters=params["passive_strategy_parameters"],
                passive_strategies=params["passive_strategies"],
                incident_irradiance_target=params["incident_irradiance_target"],
                outdoor_temperature_target=params["outdoor_temperature_target"],
                mean_radiant_temperature_target=params["mean_radiant_temperature_target"],
                air_speed_target=params["air_speed_target"],
                wind_speed_target=params["wind_speed_target"],
                comfort_parameter=params["comfort_parameter"],
                average_pressure=params["average_pressure"],
                legend_parameter=coerced_legend,
                base_point=params["base_point"],
                x_dim=1 if x_dim is None else x_dim,
                y_dim=1500 if y_dim is None else y_dim,
                min_temperature=params["min_temperature"],
                max_temperature=params["max_temperature"],
                max_humidity_ratio=params["max_humidity_ratio"],
                use_ip=params["use_ip"],
                z=params["z"],
                plot_wet_bulb=params["plot_wet_bulb"],
                name=chart_name,
                return_visualization_set=True if export_format == "html" else return_visualization_set,
            )
            if export_format == "html":
                return _finish(
                    visualization_set_to_html(
                        garden_root=root,
                        visualization_set=res["visualization_set"],
                        name=chart_name,
                        output_subdir=output_subdir or "artifacts/visualization/html",
                    )
                )
            return _finish(res)

        if chart_type == "adaptive_chart":
            root = _require_garden_root(garden_root, "adaptive_chart")
            effective_outdoor = params["outdoor_temperature_target"] or params["temperature_target"]
            if effective_outdoor is None:
                raise ValueError(
                    "outdoor_temperature_target is required for adaptive_chart."
                )
            chart_name = name or "adaptive_chart"
            res = adaptive_chart_to_visualization_set(
                garden_root=root,
                outdoor_temperature_target=effective_outdoor,
                operative_temperature_target=params["operative_temperature_target"],
                air_temperature_target=params["air_temperature_target"],
                mean_radiant_temperature_target=params["mean_radiant_temperature_target"],
                air_speed_target=params["air_speed_target"],
                relative_humidity_target=params["relative_humidity_target"],
                wind_speed_target=params["wind_speed_target"],
                comfort_parameter=params["comfort_parameter"],
                comfort_polygon=params["comfort_polygon"],
                include_passive_strategies=params["include_passive_strategies"],
                passive_strategy_parameters=params["passive_strategy_parameters"],
                passive_strategies=params["passive_strategies"],
                incident_irradiance_target=params["incident_irradiance_target"],
                average_pressure=params["average_pressure"],
                strategy_layers=_coerce_strategy_layers(params["strategy_layers"]),
                legend_parameter=coerced_legend,
                base_point=params["base_point"],
                x_dim=1 if x_dim is None else x_dim,
                y_dim=1 if y_dim is None else y_dim,
                min_prevailing=params["min_prevailing"],
                max_prevailing=params["max_prevailing"],
                min_operative=params["min_operative"],
                max_operative=params["max_operative"],
                use_ip=params["use_ip"],
                z=params["z"],
                name=chart_name,
                return_visualization_set=True if export_format == "html" else return_visualization_set,
            )
            if export_format == "html":
                return _finish(
                    visualization_set_to_html(
                        garden_root=root,
                        visualization_set=res["visualization_set"],
                        name=chart_name,
                        output_subdir=output_subdir or "artifacts/visualization/html",
                    )
                )
            return _finish(res)

        root = _require_garden_root(garden_root, "windrose")
        chart_name = name or "wind_rose"
        res = windrose_to_visualization_set(
            garden_root=root,
            direction_data_collection=params["direction_data_collection"],
            direction_data_collection_target=params["direction_data_collection_target"],
            analysis_data_collection=params["analysis_data_collection"],
            analysis_data_collection_target=params["analysis_data_collection_target"],
            direction_count=params["direction_count"],
            calm_threshold=params["calm_threshold"],
            analysis_period=params["analysis_period"],
            north=params["north"],
            show_zeros=params["show_zeros"],
            frequency_labels=params["frequency_labels"],
            legend_parameter=coerced_legend,
            name=chart_name,
            return_visualization_set=True if export_format == "html" else return_visualization_set,
        )
        if export_format == "html":
            return _finish(
                visualization_set_to_html(
                    garden_root=root,
                    visualization_set=res["visualization_set"],
                    name=chart_name,
                    output_subdir=output_subdir or "artifacts/visualization/html",
                )
            )
        return _finish(res)

    @mcp.tool(
        name="LB_Sky_To_Visualization_Set",
        tags={"ladybug", "visualization", "visualization-set", "sunpath", "skydome", "radiation-dome", "sky"},
        timeout=45,
    )
    def LB_Sky_To_Visualization_Set(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        sky_viz_type: Annotated[
            Literal[
                "sunpath",
                "skydome",
                "radiation_dome",
                "radiation_rose",
                "wind_profile",
                "view_sphere",
                "compass",
            ],
            Field(description="Sky visualization kind: sunpath, skydome, radiation_dome, radiation_rose, wind_profile, view_sphere, or compass."),
        ],
        # Sunpath inputs
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dictionary for sunpath."),
        ] = None,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Optional Garden weather target for sunpath location."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional EPW weather file path for sunpath location."),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Counterclockwise north angle (degrees) for sunpath or compass."),
        ] = 0,
        hoys: Annotated[
            list[float] | None,
            Field(description="Hours of the year to display as sun positions on sunpath."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Interpret hours as true solar time on sunpath."),
        ] = False,
        daily: Annotated[
            bool,
            Field(description="Draw hourly curves on sunpath for each day of year."),
        ] = False,
        sun_spheres: Annotated[
            bool,
            Field(description="Include 3D sun spheres along sunpath arcs."),
        ] = False,
        data_collection_targets: Annotated[
            list[DataCollectionTargetRef] | None,
            Field(description="Garden DataCollection targets mapped onto sunpath positions."),
        ] = None,
        data_collections: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Inline DataCollection dicts mapped onto sunpath positions."),
        ] = None,
        legend_parameters: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Per-collection LegendParameter dicts for sunpath overlays."),
        ] = None,
        # SkyDome / RadiationDome / RadiationRose inputs
        sky_matrix_target: Annotated[
            SkyTargetRef | None,
            Field(description="Garden SkyMatrix target for skydome, radiation_dome, or radiation_rose."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee Model target providing shading context."),
        ] = None,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameter overrides dictionary."),
        ] = None,
        plot_irradiance: Annotated[
            bool,
            Field(description="Plot irradiance (W/m2) instead of cumulative radiation (kWh/m2)."),
        ] = False,
        show_components: Annotated[
            bool,
            Field(description="Show direct and diffuse sub-components alongside total."),
        ] = False,
        include_title: Annotated[
            bool,
            Field(description="Include compass/title labels in sky VisualizationSet."),
        ] = True,
        azimuth_count: Annotated[
            int,
            Field(ge=1, description="Number of azimuth subdivisions on radiation_dome."),
        ] = 72,
        altitude_count: Annotated[
            int,
            Field(ge=1, description="Number of altitude subdivisions on radiation_dome."),
        ] = 18,
        direction_count: Annotated[
            int,
            Field(ge=3, description="Number of compass direction arrows on radiation_rose."),
        ] = 36,
        tilt_angle: Annotated[
            float,
            Field(ge=0.0, le=90.0, description="Vertical tilt angle (0-90 deg) for radiation_rose surfaces."),
        ] = 0.0,
        arrow_scale: Annotated[
            float,
            Field(gt=0.0, description="Length multiplier for radiation_rose arrows."),
        ] = 1.0,
        max_rad: Annotated[
            float | None,
            Field(gt=0.0, description="Maximum radiation bound normalizing radiation_rose arrows."),
        ] = None,
        # WindProfile inputs
        terrain: Annotated[
            Literal["city", "suburban", "country", "water", "City", "Suburban", "Country", "Water"],
            Field(description="Site terrain class for wind_profile ('city', 'suburban', 'country', 'water')."),
        ] = "city",
        meteorological_terrain: Annotated[
            Literal["city", "suburban", "country", "water", "City", "Suburban", "Country", "Water"],
            Field(description="Weather station terrain class for wind_profile."),
        ] = "country",
        meteorological_height: Annotated[
            float,
            Field(gt=0.0, description="Reference anemometer height (m) for wind_profile."),
        ] = 10.0,
        log_law: Annotated[
            bool,
            Field(description="Use logarithmic wind profile law instead of power law."),
        ] = False,
        meteorological_wind_speed: Annotated[
            float,
            Field(ge=0.0, description="Reference wind speed (m/s) for wind_profile."),
        ] = 5.0,
        direction: Annotated[
            float | None,
            Field(description="Optional wind direction vector angle (degrees) for wind_profile."),
        ] = None,
        max_height: Annotated[
            float,
            Field(gt=0.0, description="Maximum vertical profile height (m) for wind_profile."),
        ] = 30.0,
        vector_spacing: Annotated[
            float,
            Field(gt=0.0, description="Vertical spacing (m) between wind_profile vectors."),
        ] = 2.0,
        vector_length_dimension: Annotated[
            float,
            Field(gt=0.0, description="Display length scaling for wind_profile vectors."),
        ] = 5.0,
        vector_height_dimension: Annotated[
            float,
            Field(gt=0.0, description="Reference height scale for wind_profile vectors."),
        ] = 1.0,
        max_speed: Annotated[
            float | None,
            Field(gt=0.0, description="Maximum speed bound for wind_profile vector normalization."),
        ] = None,
        scale_factor: Annotated[
            float,
            Field(gt=0.0, description="Overall geometric scale factor for wind_profile."),
        ] = 1.0,
        feet_labels: Annotated[
            bool,
            Field(description="Format wind_profile height labels in feet instead of meters."),
        ] = False,
        # ViewSphere inputs
        view_type: Annotated[
            Literal["HorizontalRadial", "Horizontal30DegreeOffset", "Spherical", "SkyExposure", "SkyView"],
            Field(description="ViewSphere geometry mode: HorizontalRadial, Horizontal30DegreeOffset, Spherical, SkyExposure, or SkyView."),
        ] = "HorizontalRadial",
        resolution: Annotated[
            int,
            Field(ge=1, description="ViewSphere vector subdivision level (>= 1)."),
        ] = 1,
        context_intersect_dist: Annotated[
            list[float] | None,
            Field(description="Ray intersection distances matching ViewSphere vectors."),
        ] = None,
        dist_units: Annotated[
            str,
            Field(description="Distance unit label for ViewSphere legend ('m', 'ft', etc.)."),
        ] = "m",
        draw_view_rays: Annotated[
            bool,
            Field(description="Include ViewSphere direction rays as ContextGeometry."),
        ] = True,
        # Compass inputs
        spacing_factor: Annotated[
            float,
            Field(gt=0.0, description="Text spacing ratio relative to compass radius."),
        ] = 0.15,
        custom_angles: Annotated[
            list[float] | None,
            Field(description="Additional azimuth angles (degrees) marked on compass."),
        ] = None,
        font: Annotated[
            str,
            Field(description="Font family name for compass labels."),
        ] = "Arial",
        maj_txt_size: Annotated[
            float | None,
            Field(gt=0.0, description="Major cardinal text height on compass."),
        ] = None,
        min_txt_size: Annotated[
            float | None,
            Field(gt=0.0, description="Minor degree text height on compass."),
        ] = None,
        # Shared spatial / output parameters
        radius: Annotated[
            float,
            Field(gt=0.0, description="Display radius for sky dome, sunpath, compass, or view sphere."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="3D center Point3D (dict or [x,y,z]) for sky geometry placement."),
        ] = None,
        projection: Annotated[
            Literal[
                "Orthographic",
                "Stereographic",
                "Equidistant",
                "Equisolid",
                "orthographic",
                "stereographic",
                "equidistant",
                "equisolid",
            ]
            | None,
            Field(description="Optional 2D dome projection: Orthographic, Stereographic, Equidistant, or Equisolid."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Include the full VisualizationSet dictionary in the response."),
        ] = True,
    ) -> MutationResultModel:
        """Generate a Sunpath, SkyDome, RadiationDome, RadiationRose, WindProfile, ViewSphere, or Compass VisualizationSet."""
        coerced_legend = coerce_legend_parameter_dict(dump_input(legend_parameter))
        coerced_legends = (
            [coerce_legend_parameter_dict(dump_input(lp)) for lp in legend_parameters]
            if legend_parameters
            else None
        )
        dumped_weather_target = dump_target(weather_target)
        dumped_dc_targets = dump_targets(data_collection_targets)
        dumped_sky_target = dump_target(sky_matrix_target)
        dumped_model_target = dump_target(model_target)
        dumped_center_point = dump_input(center_point)
        dumped_location = dump_input(location)
        dumped_collections = dump_input(data_collections)

        if sky_viz_type == "sunpath":
            return validate_output(
                MutationResultModel,
                sunpath_to_visualization_set(
                    garden_root=garden_root,
                    location=dumped_location,
                    weather_target=dumped_weather_target,
                    epw_path=epw_path,
                    north_angle=north_angle,
                    hoys=hoys,
                    data_collection_targets=dumped_dc_targets,
                    data_collections=dumped_collections,
                    legend_parameter=coerced_legend,
                    legend_parameters=coerced_legends,
                    radius=radius,
                    center_point=dumped_center_point,
                    solar_time=solar_time,
                    daily=daily,
                    projection=projection,
                    sun_spheres=sun_spheres,
                    name=name or "sunpath",
                    return_visualization_set=return_visualization_set,
                ),
            )

        if sky_viz_type == "wind_profile":
            return validate_output(
                MutationResultModel,
                wind_profile_to_visualization_set(
                    garden_root=garden_root,
                    terrain=terrain,
                    meteorological_terrain=meteorological_terrain,
                    meteorological_height=meteorological_height,
                    log_law=log_law,
                    meteorological_wind_speed=meteorological_wind_speed,
                    direction=direction,
                    legend_parameter=coerced_legend,
                    center_point=dumped_center_point,
                    max_height=max_height,
                    vector_spacing=vector_spacing,
                    vector_length_dimension=vector_length_dimension,
                    vector_height_dimension=vector_height_dimension,
                    max_speed=max_speed,
                    scale_factor=scale_factor,
                    feet_labels=feet_labels,
                    name=name or "wind_profile",
                    return_visualization_set=return_visualization_set,
                ),
            )

        if sky_viz_type == "view_sphere":
            return validate_output(
                MutationResultModel,
                view_sphere_to_visualization_set(
                    garden_root=garden_root,
                    view_type=view_type,
                    resolution=resolution,
                    center_point=dumped_center_point,
                    context_intersect_dist=context_intersect_dist,
                    dist_units=dist_units,
                    radius=radius if radius != 100 else 1.0,
                    legend_parameter=coerced_legend,
                    draw_view_rays=draw_view_rays,
                    name=name or "view_sphere",
                    return_visualization_set=return_visualization_set,
                ),
            )

        if sky_viz_type == "compass":
            return validate_output(
                MutationResultModel,
                compass_to_visualization_set(
                    garden_root=garden_root,
                    radius=radius,
                    center_point=dumped_center_point,
                    north_angle=north_angle,
                    spacing_factor=spacing_factor,
                    custom_angles=custom_angles,
                    projection=projection,
                    font=font,
                    maj_txt_size=maj_txt_size,
                    min_txt_size=min_txt_size,
                    name=name or "compass",
                    return_visualization_set=return_visualization_set,
                ),
            )

        if dumped_sky_target is None:
            raise ValueError(
                f"sky_matrix_target is required for sky_viz_type={sky_viz_type!r}."
            )

        if sky_viz_type == "skydome":
            return validate_output(
                MutationResultModel,
                sky_matrix_to_skydome_visualization_set(
                    garden_root=garden_root,
                    sky_matrix_target=dumped_sky_target,
                    legend_parameter=coerced_legend,
                    plot_irradiance=plot_irradiance,
                    radius=radius,
                    center_point=dumped_center_point,
                    projection=projection,
                    show_components=show_components,
                    include_title=include_title,
                    name=name or "sky_dome",
                    return_visualization_set=return_visualization_set,
                ),
            )

        if sky_viz_type == "radiation_rose":
            return validate_output(
                MutationResultModel,
                sky_matrix_to_radiation_rose_visualization_set(
                    garden_root=garden_root,
                    sky_matrix_target=dumped_sky_target,
                    model_target=dumped_model_target,
                    direction_count=direction_count,
                    tilt_angle=tilt_angle,
                    arrow_scale=arrow_scale,
                    max_rad=max_rad,
                    legend_parameter=coerced_legend,
                    plot_irradiance=plot_irradiance,
                    radius=radius,
                    center_point=dumped_center_point,
                    show_components=show_components,
                    include_title=include_title,
                    name=name or "radiation_rose",
                    return_visualization_set=return_visualization_set,
                ),
            )

        return validate_output(
            MutationResultModel,
            sky_matrix_to_radiation_dome_visualization_set(
                garden_root=garden_root,
                sky_matrix_target=dumped_sky_target,
                model_target=dumped_model_target,
                azimuth_count=azimuth_count,
                altitude_count=altitude_count,
                legend_parameter=coerced_legend,
                plot_irradiance=plot_irradiance,
                radius=radius,
                center_point=dumped_center_point,
                projection=projection,
                show_components=show_components,
                include_title=include_title,
                name=name or "radiation_dome",
                return_visualization_set=return_visualization_set,
            ),
        )

    @mcp.tool(
        name="LB_Compose_Visualization_Sets",
        tags={"ladybug", "visualization", "visualization-set", "compose", "overlay", "target"},
        timeout=30,
    )
    def LB_Compose_Visualization_Sets(
        visualization_sets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Inline VisualizationSet dicts to merge together."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root directory for resolving VisualizationSet targets."),
        ] = None,
        visualization_set_targets: Annotated[
            list[ArtifactTargetRef] | None,
            Field(description="Garden targets for VisualizationSets to compose."),
        ] = None,
        model_context_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Model-context VisualizationSet target for model-analysis overlay."),
        ] = None,
        analysis_visualization_set_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Analysis VisualizationSet target overlaid onto model_context_target."),
        ] = None,
        exclude_context_geometry_identifiers: Annotated[
            list[str] | None,
            Field(description="Context geometry IDs stripped from model_context_target (default ['Sensor_Grids'])."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional display name for the composed VisualizationSet."),
        ] = None,
        units: Annotated[
            Literal["Meters", "Millimeters", "Feet", "Inches", "Centimeters"] | None,
            Field(description="Optional units override on the composed VisualizationSet."),
        ] = None,
        check_duplicate_geometry_ids: Annotated[
            bool,
            Field(description="Detect and handle duplicate geometry identifiers across inputs."),
        ] = True,
        conflict_strategy: Annotated[
            Literal["error", "rename", "overwrite", "skip"] | None,
            Field(description="Duplicate geometry ID policy: 'error', 'rename', 'overwrite', or 'skip'."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Include full VisualizationSet dictionary in the response."),
        ] = True,
    ) -> MutationResultModel:
        """Compose VisualizationSets or overlay an analysis layer onto a model-context set."""
        dumped_model_context = dump_target(model_context_target)
        dumped_analysis_vs = dump_target(analysis_visualization_set_target)
        dumped_vis_targets = dump_targets(visualization_set_targets)

        if (dumped_model_context is not None) != (
            dumped_analysis_vs is not None
        ):
            raise ValueError(
                "Both model_context_target and analysis_visualization_set_target are required for model-analysis overlay."
            )
        if (
            dumped_model_context is not None
            and dumped_analysis_vs is not None
        ):
            root = _require_garden_root(
                garden_root, "model-analysis VisualizationSet overlay"
            )
            return validate_output(
                MutationResultModel,
                compose_model_analysis_visualization_set(
                    garden_root=root,
                    model_context_target=dumped_model_context,
                    analysis_visualization_set_target=dumped_analysis_vs,
                    name=name or "model_analysis_overlay",
                    units=units,
                    exclude_context_geometry_identifiers=exclude_context_geometry_identifiers,
                    conflict_strategy=conflict_strategy or "rename",
                    return_visualization_set=return_visualization_set,
                ),
            )
        return validate_output(
            MutationResultModel,
            compose_visualization_sets(
                visualization_sets=visualization_sets,
                garden_root=garden_root,
                visualization_set_targets=dumped_vis_targets,
                name=name,
                units=units,
                check_duplicate_geometry_ids=check_duplicate_geometry_ids,
                conflict_strategy=conflict_strategy or "error",
                return_visualization_set=return_visualization_set,
            ),
        )

    @mcp.tool(
        name="LB_Export_Visualization_Set",
        tags={"ladybug", "visualization", "visualization-set", "export", "html", "svg", "vtkjs", "artifact"},
        timeout=60,
    )
    def LB_Export_Visualization_Set(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        export_format: Annotated[
            Literal["html", "svg", "vtkjs", "png", "vtk", "vtp", "vsf", "pkl"],
            Field(description="Export format: html, svg, vtkjs, png, vtk, vtp, vsf, or pkl."),
        ],
        visualization_set: Annotated[
            dict[str, Any] | None,
            Field(description="Inline VisualizationSet dictionary to export."),
        ] = None,
        visualization_set_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Garden target for a persisted VisualizationSet to export."),
        ] = None,
        name: Annotated[
            str,
            Field(description="Base filename for the exported artifact."),
        ] = "visualization_set",
        output_subdir: Annotated[
            str | None,
            Field(description="Relative Garden subdirectory for the exported file."),
        ] = None,
        open: Annotated[
            bool,
            Field(description="Open the generated HTML artifact in a browser after export."),
        ] = False,
        width: Annotated[
            int,
            Field(ge=1, description="Rendered image width in pixels for SVG/PNG export."),
        ] = 1600,
        height: Annotated[
            int,
            Field(ge=1, description="Rendered image height in pixels for SVG/PNG export."),
        ] = 900,
        view: Annotated[
            str | dict[str, Any],
            Field(description="Named camera view (Top, Front, NE, SW, etc.) or Plane dict for SVG/PNG."),
        ] = "Top",
        margin: Annotated[
            float | None,
            Field(ge=0.0, description="Viewport margin fraction for SVG/PNG export."),
        ] = None,
        interactive: Annotated[
            bool,
            Field(description="Generate interactive SVG/PNG controls where supported."),
        ] = False,
        render_2d_legend: Annotated[
            bool,
            Field(description="Include 2D legends in the SVG/PNG/HTML export."),
        ] = True,
        render_3d_legend: Annotated[
            bool,
            Field(description="Include 3D legends in the export."),
        ] = False,
        auto_crop: Annotated[
            bool,
            Field(description="Crop SVG canvas/viewBox tightly to visible elements and legends (default True)."),
        ] = True,
    ) -> ArtifactResultModel:
        """Export a VisualizationSet dictionary or Garden target to HTML, SVG, VTKJS, PNG, VTK, VTP, VSF, or PKL."""
        return validate_output(
            ArtifactResultModel,
            export_visualization_set(
                garden_root=garden_root,
                export_format=export_format,
                visualization_set=visualization_set,
                visualization_set_target=dump_target(visualization_set_target),
                name=name,
                output_subdir=output_subdir,
                open=open,
                width=width,
                height=height,
                view=view,
                margin=margin,
                interactive=interactive,
                render_2d_legend=render_2d_legend,
                render_3d_legend=render_3d_legend,
                auto_crop=auto_crop,
            ),
        )

    @mcp.tool(
        name="LB_Data_Collection_To_File",
        tags={"ladybug", "data-collection", "export", "json", "csv", "pkl", "artifact"},
        timeout=30,
    )
    def LB_Data_Collection_To_File(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(description="Inline Ladybug DataCollection dict to export."),
        ] = None,
        data_collection_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for a persisted DataCollection to export."),
        ] = None,
        data_collections: Annotated[
            list[dict[str, Any]] | None,
            Field(description="List of inline DataCollection dicts for multi-series export."),
        ] = None,
        data_collection_targets: Annotated[
            list[DataCollectionTargetRef] | None,
            Field(description="List of Garden DataCollection targets for multi-series export."),
        ] = None,
        file_format: Annotated[
            Literal["json", "csv", "pkl"],
            Field(description="Export file format: 'json', 'csv', or 'pkl'."),
        ] = "json",
        name: Annotated[
            str,
            Field(description="Base filename for the exported DataCollection artifact."),
        ] = "data_collection",
        output_subdir: Annotated[
            str,
            Field(description="Relative Garden subdirectory for exported files."),
        ] = "artifacts/data_collections",
    ) -> ArtifactResultModel:
        """Export one or more Ladybug DataCollection dicts or targets to a JSON, CSV, or PKL artifact."""
        return validate_output(
            ArtifactResultModel,
            export_data_collection_file(
                garden_root=garden_root,
                data_collection=data_collection,
                data_collection_target=dump_target(data_collection_target),
                data_collections=data_collections,
                data_collection_targets=dump_targets(data_collection_targets),
                file_format=file_format,
                name=name,
                output_subdir=output_subdir,
                source={"producer": "LB_Data_Collection_To_File"},
            ),
        )

    @mcp.tool(
        name="LB_Run_Solar_Geometry_Study",
        tags={
            "ladybug",
            "ladybug-radiance",
            "solar",
            "direct-sun",
            "radiation",
            "solar-envelope",
            "view-sphere",
            "shade-benefit",
            "ray-tracing",
            "view-percent",
            "view-rose",
            "visualization-set",
        },
        timeout=120,
    )
    def LB_Run_Solar_Geometry_Study(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        study_type: Annotated[
            Literal[
                "direct_sun",
                "radiation",
                "solar_envelope",
                "sky_intersection",
                "view_sphere",
                "shade_benefit",
                "thermal_shade_benefit",
                "surface_ray_tracing",
                "view_percent",
                "view_rose",
            ],
            Field(description="Solar geometry study type to execute."),
        ],
        study_mesh: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Mesh3D dict to analyze."),
        ] = None,
        study_face: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Face3D dict to tessellate and analyze."),
        ] = None,
        context_geometry: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Explicit Face3D or Mesh3D obstruction geometry dicts."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee Model target supplying study/context geometry."),
        ] = None,
        study_face_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Honeybee Face targets from model_target to analyze."),
        ] = None,
        study_room_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Honeybee Room targets from model_target to analyze."),
        ] = None,
        face_type_filter: Annotated[
            str | None,
            Field(description="Optional Honeybee face type filter (e.g., Wall, RoofCeiling)."),
        ] = None,
        grid_size: Annotated[
            float | None,
            Field(gt=0.0, description="Mesh tessellation size in model units when subdividing faces."),
        ] = None,
        vectors: Annotated[
            list[list[float] | dict[str, Any]] | None,
            Field(description="Explicit sun vectors for direct_sun or shade_benefit studies."),
        ] = None,
        sky_matrix_target: Annotated[
            SkyTargetRef | None,
            Field(description="Garden SkyMatrix target for radiation or sky_intersection studies."),
        ] = None,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Garden weather target supplying sunpath or sky data."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="EPW file path when weather_target is omitted."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dict when weather_target/epw_path are omitted."),
        ] = None,
        hoys: Annotated[
            list[float] | None,
            Field(description="Hours of the year for direct_sun or sky studies."),
        ] = None,
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional AnalysisPeriod dict or string for sun studies."),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0.0,
        solar_time: Annotated[
            bool,
            Field(description="Interpret sun study hours as true solar time."),
        ] = False,
        timestep: Annotated[
            int,
            Field(ge=1, description="Timesteps per hour for sunpath study calculations."),
        ] = 1,
        high_density: Annotated[
            bool,
            Field(description="Use 577-patch Reinhart sky subdivision instead of 145-patch Tregenza."),
        ] = False,
        ground_reflectance: Annotated[
            float,
            Field(ge=0.0, le=1.0, description="Ground albedo reflectance (0-1) for radiation study."),
        ] = 0.2,
        benefit: Annotated[
            bool,
            Field(description="Evaluate heating vs cooling radiation benefit using balance_temperature."),
        ] = False,
        balance_temperature: Annotated[
            float,
            Field(description="Outdoor balance temperature (C) for radiation benefit."),
        ] = 15.0,
        balance_offset: Annotated[
            float,
            Field(description="Neutral deadband offset (C) around balance_temperature."),
        ] = 2.0,
        plot_irradiance: Annotated[
            bool,
            Field(description="Output average irradiance (W/m2) instead of radiation (kWh/m2)."),
        ] = False,
        offset_distance: Annotated[
            float,
            Field(description="Offset distance along face normals for study grid points."),
        ] = 0.0,
        by_vertex: Annotated[
            bool,
            Field(description="Compute results at mesh vertices rather than face centroids."),
        ] = False,
        use_radiance_mesh: Annotated[
            bool,
            Field(description="Use Radiance-style mesh conversion when building geometry."),
        ] = False,
        height_limit: Annotated[
            float,
            Field(gt=0.0, description="Maximum vertical envelope height (m) for solar_envelope."),
        ] = 100.0,
        solar_rights: Annotated[
            bool,
            Field(description="Compute a solar rights envelope rather than solar collection."),
        ] = False,
        view_type: Annotated[
            Literal[
                "HorizontalRadial",
                "Horizontal30DegreeOffset",
                "Spherical",
                "SkyExposure",
                "SkyView",
                "horizontal_radial",
                "horizontal_30_degree_offset",
                "spherical",
                "sky_exposure",
                "sky_view",
                "horizontalradial",
                "horizontal30degreeoffset",
                "skyexposure",
                "skyview",
            ],
            Field(description="View analysis metric: HorizontalRadial, Horizontal30DegreeOffset, Spherical, SkyExposure, or SkyView."),
        ] = "SkyExposure",
        resolution: Annotated[
            int,
            Field(ge=1, description="View sphere ray subdivision factor (>= 1)."),
        ] = 1,
        center_point: Annotated[
            list[float] | dict[str, Any] | None,
            Field(description="3D origin Point3D (dict or [x,y,z]) for view_sphere or view_rose."),
        ] = None,
        radius: Annotated[
            float,
            Field(gt=0.0, description="Sphere/rose radius for view_sphere or view_rose studies."),
        ] = 5.0,
        numericalize: Annotated[
            bool,
            Field(description="Store numeric view intersection distances on view_sphere."),
        ] = False,
        geo_block: Annotated[
            bool | None,
            Field(description="Flag faces occluded behind view_sphere geometry."),
        ] = None,
        include_view_rose: Annotated[
            bool,
            Field(description="Overlay a 3D view rose on view_percent results."),
        ] = False,
        draw_view_rays: Annotated[
            bool,
            Field(description="Include view rays in view_sphere/view_rose VisualizationSet."),
        ] = True,
        shade_geometry: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Shade geometry dicts evaluated for shade_benefit / thermal_shade_benefit."),
        ] = None,
        study_region: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Target aperture/face dicts receiving shade benefit."),
        ] = None,
        study_points: Annotated[
            list[list[float] | dict[str, Any]] | None,
            Field(description="Explicit test points for view_percent or ray tracing."),
        ] = None,
        study_directions: Annotated[
            list[list[float] | dict[str, Any]] | None,
            Field(description="Directional normals aligned with study_points."),
        ] = None,
        temperature_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden dry-bulb temperature target for shade_benefit."),
        ] = None,
        up_threshold: Annotated[
            float,
            Field(description="Upper helpful-shade temperature/comfort threshold (C)."),
        ] = 26.0,
        low_threshold: Annotated[
            float,
            Field(description="Lower harmful-shade temperature/comfort threshold (C)."),
        ] = 9.0,
        source_geometry: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Source point/surface geometry dicts for surface_ray_tracing."),
        ] = None,
        receiver_geometry: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Receiver surface geometry dicts for surface_ray_tracing."),
        ] = None,
        bounce_count: Annotated[
            int,
            Field(ge=1, description="Number of specular ray bounces for surface_ray_tracing."),
        ] = 1,
        first_length: Annotated[
            float | None,
            Field(gt=0.0, description="Length limit for initial ray segments."),
        ] = None,
        last_length: Annotated[
            float | None,
            Field(gt=0.0, description="Length limit for final ray segments."),
        ] = None,
        context_block: Annotated[
            bool,
            Field(description="Include context_geometry intersections for shade_benefit / view."),
        ] = False,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameter overrides dictionary."),
        ] = None,
        include_title: Annotated[
            bool,
            Field(description="Include legend/study title text in VisualizationSet."),
        ] = True,
        include_context: Annotated[
            bool,
            Field(description="Include context_geometry in returned VisualizationSet."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Include raw numeric result array in response payload."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Include the full VisualizationSet dictionary in the response."),
        ] = True,
    ) -> MutationResultModel:
        """Run DirectSunStudy, RadiationStudy, SolarEnvelope, SkyIntersection, ViewSphere, ShadeBenefit, ThermalShadeBenefit, SurfaceRayTracing, ViewPercent, or ViewRose study."""
        return validate_output(
            MutationResultModel,
            run_solar_geometry_study(
                garden_root=garden_root,
                study_type=study_type,
                study_mesh=study_mesh,
                study_face=study_face,
                context_geometry=context_geometry,
                model_target=dump_target(model_target),
                study_face_targets=dump_targets(study_face_targets),
                study_room_targets=dump_targets(study_room_targets),
                face_type_filter=face_type_filter,
                grid_size=grid_size,
                vectors=vectors,
                sky_matrix_target=dump_target(sky_matrix_target),
                weather_target=dump_target(weather_target),
                epw_path=epw_path,
                location=location,
                hoys=hoys,
                analysis_period=dump_input(analysis_period),
                north_angle=north_angle,
                solar_time=solar_time,
                timestep=timestep,
                high_density=high_density,
                ground_reflectance=ground_reflectance,
                benefit=benefit,
                balance_temperature=balance_temperature,
                balance_offset=balance_offset,
                plot_irradiance=plot_irradiance,
                offset_distance=offset_distance,
                by_vertex=by_vertex,
                use_radiance_mesh=use_radiance_mesh,
                height_limit=height_limit,
                solar_rights=solar_rights,
                view_type=view_type,
                resolution=resolution,
                center_point=dump_input(center_point),
                radius=radius,
                numericalize=numericalize,
                geo_block=geo_block,
                include_view_rose=include_view_rose,
                draw_view_rays=draw_view_rays,
                shade_geometry=shade_geometry,
                study_region=study_region,
                study_points=study_points,
                study_directions=study_directions,
                temperature_target=dump_target(temperature_target),
                up_threshold=up_threshold,
                low_threshold=low_threshold,
                source_geometry=source_geometry,
                receiver_geometry=receiver_geometry,
                bounce_count=bounce_count,
                first_length=first_length,
                last_length=last_length,
                context_block=context_block,
                legend_parameter=coerce_legend_parameter_dict(dump_input(legend_parameter)),
                include_title=include_title,
                include_context=include_context,
                include_values=include_values,
                name=name,
                return_visualization_set=return_visualization_set,
            ),
        )
