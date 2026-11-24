"""Consolidated MCP tools for Ladybug/Honeybee visualization and export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

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
        garden_root: str,
        target: dict[str, Any] | None = None,
        model_target: dict[str, Any] | None = None,
        color_by: str | None = "type",
        include_wireframe: bool = True,
        wireframe_only: bool = False,
        use_mesh: bool = False,
        hide_color_by: bool = False,
        room_attributes: list[dict[str, Any]] | None = None,
        face_attributes: list[dict[str, Any]] | None = None,
        include_sub_faces: bool = True,
        include_shades: bool = True,
        name: str | None = None,
        return_visualization_set: bool = True,
    ) -> dict[str, Any]:
        """Convert a Honeybee Model, Room, or Face to a VisualizationSet."""
        if target is None or target.get("object_type") == "model":
            return honeybee_model_to_visualization_set(
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
        object_type = target.get("object_type")
        if object_type == "room":
            return honeybee_room_to_visualization_set(
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
        if object_type == "face":
            return honeybee_face_to_visualization_set(
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
        raise ValueError(
            f"Unsupported Honeybee object_type in target: {object_type!r}. Expected 'room', 'face', or omit target for full model."
        )

    @mcp.tool(
        name="LB_Chart_To_Visualization_Set",
        tags={"ladybug", "visualization", "visualization-set", "chart", "hourly-plot", "monthly-chart", "psychrometric", "windrose", "html", "legend"},
        timeout=45,
    )
    def LB_Chart_To_Visualization_Set(
        chart_type: Literal[
            "hourly_plot",
            "monthly_chart",
            "psychrometric_chart",
            "adaptive_chart",
            "windrose",
        ],
        export_format: Literal["visualization_set", "html"] = "visualization_set",
        garden_root: str | None = None,
        legend_parameter: dict[str, Any] | None = None,
        x_dim: float | None = None,
        y_dim: float | None = None,
        name: str | None = None,
        output_subdir: str | None = None,
        return_visualization_set: bool = True,
        # Energy SQL input options (hourly_plot / monthly_chart)
        energy_run_target: dict[str, Any] | None = None,
        run_id: str | None = None,
        output_name: str | None = None,
        collection_index: int = 0,
        run_period_index: int | None = None,
        # Hourly plot / Monthly chart DataCollection inputs
        data_collection: dict[str, Any] | None = None,
        data_collection_target: dict[str, Any] | None = None,
        series: list[dict[str, Any]] | None = None,
        time_interval: str = "as_is",
        chart_title: str | None = None,
        y_axis_title: str | None = None,
        stack: bool = False,
        percentile: float = 34,
        time_marks: bool = False,
        # Psychrometric chart options
        temperature_target: dict[str, Any] | None = None,
        relative_humidity_target: dict[str, Any] | None = None,
        strategy_layers: list[dict[str, Any]] | None = None,
        average_pressure: float = 101325,
        base_point: dict[str, Any] | list[float] | None = None,
        min_temperature: float = -20,
        max_temperature: float = 50,
        max_humidity_ratio: float = 0.03,
        use_ip: bool = False,
        z: float = 0,
        plot_wet_bulb: bool = False,
        # Windrose options
        direction_data_collection: dict[str, Any] | None = None,
        direction_data_collection_target: dict[str, Any] | None = None,
        analysis_data_collection: dict[str, Any] | None = None,
        analysis_data_collection_target: dict[str, Any] | None = None,
        direction_count: int = 36,
        calm_threshold: float = 1e-10,
        analysis_period: dict[str, Any] | str | None = None,
        north: float = 0.0,
        show_zeros: bool = False,
        frequency_labels: bool = True,
        # HourlyPlot & MonthlyChart upgrades
        z_dim: float = 0.0,
        reverse_y: bool = False,
        custom_hours: list[int] | None = None,
        y_axis_min: list[float | None] | float | None = None,
        y_axis_max: list[float | None] | float | None = None,
        # Psychrometric & Adaptive chart comfort polygons / inputs
        comfort_polygon: dict[str, Any] | None = None,
        include_passive_strategies: bool = True,
        passive_strategy_parameters: dict[str, Any] | None = None,
        passive_strategies: list[str] | None = None,
        incident_irradiance_target: dict[str, Any] | None = None,
        outdoor_temperature_target: dict[str, Any] | None = None,
        operative_temperature_target: dict[str, Any] | None = None,
        air_temperature_target: dict[str, Any] | None = None,
        mean_radiant_temperature_target: dict[str, Any] | None = None,
        air_speed_target: dict[str, Any] | None = None,
        wind_speed_target: dict[str, Any] | None = None,
        comfort_parameter: dict[str, Any] | None = None,
        min_prevailing: float = 10,
        max_prevailing: float = 33,
        min_operative: float = 14,
        max_operative: float = 40,
    ) -> dict[str, Any]:
        """Build an HourlyPlot, MonthlyChart, PsychrometricChart, or WindRose VisualizationSet or HTML.

        Accepts inline ``legend_parameter`` dictionaries (including 2D legend
        fields like ``origin``, ``segment_height``, ``segment_width``,
        ``color_set``, ``min``/``max``), DataCollection dicts/targets, and
        EnergyPlus SQL run inputs for hourly/monthly charts.
        """
        coerced_legend = coerce_legend_parameter_dict(legend_parameter)

        if chart_type == "hourly_plot":
            chart_name = name or (
                "energy_result_hourly_plot"
                if (energy_run_target is not None or run_id is not None or output_name is not None)
                else "data_collection_hourly_plot"
            )
            is_sql_input = (
                data_collection is None
                and data_collection_target is None
                and (energy_run_target is not None or run_id is not None or output_name is not None)
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
                    return energy_result_hourly_plot_to_html(
                        garden_root=root,
                        run_target=energy_run_target,
                        run_id=run_id,
                        output_name=output_name,
                        collection_index=collection_index,
                        name=chart_name,
                        output_subdir=output_subdir or "artifacts/energy/results/html",
                    )
                data_collection = _extract_energy_hourly_collection(
                    garden_root=root,
                    energy_run_target=energy_run_target,
                    run_id=run_id,
                    output_name=output_name,
                    collection_index=collection_index,
                    run_period_index=run_period_index,
                )

            if export_format == "html":
                root = _require_garden_root(garden_root, "hourly_plot HTML export")
                return data_collection_hourly_plot_to_html(
                    garden_root=root,
                    data_collection=data_collection,
                    data_collection_target=data_collection_target,
                    legend_parameter=coerced_legend,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    z_dim=z_dim,
                    reverse_y=reverse_y,
                    custom_hours=custom_hours,
                    name=chart_name,
                    output_subdir=output_subdir or "artifacts/visualization/datacollections/html",
                )
            return data_collection_hourly_plot_to_visualization_set(
                data_collection=data_collection,
                data_collection_target=data_collection_target,
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

        if chart_type == "monthly_chart":
            if not series:
                raise ValueError("series must include at least one entry for monthly_chart.")
            is_sql_series = (
                energy_run_target is not None
                or run_id is not None
                or any(
                    isinstance(item, dict)
                    and "output_name" in item
                    and "data_collection" not in item
                    and "data_collection_target" not in item
                    for item in series
                )
            )
            chart_name = name or (
                "energy_result_monthly_chart"
                if is_sql_series
                else "data_collection_monthly_chart"
            )
            effective_time_interval = time_interval
            resolved_series = series
            if is_sql_series:
                root = _require_garden_root(garden_root, "Energy SQL monthly_chart")
                if (
                    export_format == "html"
                    and coerced_legend is None
                    and x_dim is None
                    and y_dim is None
                ):
                    return energy_result_monthly_chart_to_html(
                        garden_root=root,
                        series=series,
                        run_target=energy_run_target,
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
                resolved_series = _extract_energy_monthly_series(
                    garden_root=root,
                    energy_run_target=energy_run_target,
                    run_id=run_id,
                    series=series,
                    time_interval=time_interval,
                )
                effective_time_interval = "as_is"

            if export_format == "html":
                root = _require_garden_root(garden_root, "monthly_chart HTML export")
                return data_collection_monthly_chart_to_html(
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
            return data_collection_monthly_chart_to_visualization_set(
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

        if chart_type == "psychrometric_chart":
            root = _require_garden_root(garden_root, "psychrometric_chart")
            if temperature_target is None or relative_humidity_target is None:
                raise ValueError(
                    "temperature_target and relative_humidity_target are required for psychrometric_chart."
                )
            chart_name = name or "psychrometric_chart"
            res = psychrometric_chart_to_visualization_set(
                garden_root=root,
                temperature_target=temperature_target,
                relative_humidity_target=relative_humidity_target,
                strategy_layers=_coerce_strategy_layers(strategy_layers),
                comfort_polygon=comfort_polygon,
                include_passive_strategies=include_passive_strategies,
                passive_strategy_parameters=passive_strategy_parameters,
                passive_strategies=passive_strategies,
                incident_irradiance_target=incident_irradiance_target,
                outdoor_temperature_target=outdoor_temperature_target,
                mean_radiant_temperature_target=mean_radiant_temperature_target,
                air_speed_target=air_speed_target,
                wind_speed_target=wind_speed_target,
                comfort_parameter=comfort_parameter,
                average_pressure=average_pressure,
                legend_parameter=coerced_legend,
                base_point=base_point,
                x_dim=1 if x_dim is None else x_dim,
                y_dim=1500 if y_dim is None else y_dim,
                min_temperature=min_temperature,
                max_temperature=max_temperature,
                max_humidity_ratio=max_humidity_ratio,
                use_ip=use_ip,
                z=z,
                plot_wet_bulb=plot_wet_bulb,
                name=chart_name,
                return_visualization_set=True if export_format == "html" else return_visualization_set,
            )
            if export_format == "html":
                return visualization_set_to_html(
                    garden_root=root,
                    visualization_set=res["visualization_set"],
                    name=chart_name,
                    output_subdir=output_subdir or "artifacts/visualization/html",
                )
            return res

        if chart_type == "adaptive_chart":
            root = _require_garden_root(garden_root, "adaptive_chart")
            effective_outdoor = outdoor_temperature_target or temperature_target
            if effective_outdoor is None:
                raise ValueError(
                    "outdoor_temperature_target is required for adaptive_chart."
                )
            chart_name = name or "adaptive_chart"
            res = adaptive_chart_to_visualization_set(
                garden_root=root,
                outdoor_temperature_target=effective_outdoor,
                operative_temperature_target=operative_temperature_target,
                air_temperature_target=air_temperature_target,
                mean_radiant_temperature_target=mean_radiant_temperature_target,
                air_speed_target=air_speed_target,
                relative_humidity_target=relative_humidity_target,
                wind_speed_target=wind_speed_target,
                comfort_parameter=comfort_parameter,
                comfort_polygon=comfort_polygon,
                include_passive_strategies=include_passive_strategies,
                passive_strategy_parameters=passive_strategy_parameters,
                passive_strategies=passive_strategies,
                incident_irradiance_target=incident_irradiance_target,
                average_pressure=average_pressure,
                strategy_layers=_coerce_strategy_layers(strategy_layers),
                legend_parameter=coerced_legend,
                base_point=base_point,
                x_dim=1 if x_dim is None else x_dim,
                y_dim=1 if y_dim is None else y_dim,
                min_prevailing=min_prevailing,
                max_prevailing=max_prevailing,
                min_operative=min_operative,
                max_operative=max_operative,
                use_ip=use_ip,
                z=z,
                name=chart_name,
                return_visualization_set=True if export_format == "html" else return_visualization_set,
            )
            if export_format == "html":
                return visualization_set_to_html(
                    garden_root=root,
                    visualization_set=res["visualization_set"],
                    name=chart_name,
                    output_subdir=output_subdir or "artifacts/visualization/html",
                )
            return res

        root = _require_garden_root(garden_root, "windrose")
        chart_name = name or "wind_rose"
        res = windrose_to_visualization_set(
            garden_root=root,
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
            legend_parameter=coerced_legend,
            name=chart_name,
            return_visualization_set=True if export_format == "html" else return_visualization_set,
        )
        if export_format == "html":
            return visualization_set_to_html(
                garden_root=root,
                visualization_set=res["visualization_set"],
                name=chart_name,
                output_subdir=output_subdir or "artifacts/visualization/html",
            )
        return res

    @mcp.tool(
        name="LB_Sky_To_Visualization_Set",
        tags={"ladybug", "visualization", "visualization-set", "sunpath", "skydome", "radiation-dome", "sky"},
        timeout=45,
    )
    def LB_Sky_To_Visualization_Set(
        garden_root: str,
        sky_viz_type: Literal[
            "sunpath",
            "skydome",
            "radiation_dome",
            "radiation_rose",
            "wind_profile",
            "view_sphere",
            "compass",
        ],
        # Sunpath inputs
        location: dict[str, Any] | None = None,
        weather_target: dict[str, Any] | None = None,
        epw_path: str | None = None,
        north_angle: float = 0,
        hoys: list[float] | None = None,
        solar_time: bool = False,
        daily: bool = False,
        sun_spheres: bool = False,
        data_collection_targets: list[dict[str, Any]] | None = None,
        data_collections: list[dict[str, Any]] | None = None,
        legend_parameters: list[dict[str, Any]] | None = None,
        # SkyDome / RadiationDome / RadiationRose inputs
        sky_matrix_target: dict[str, Any] | None = None,
        model_target: dict[str, Any] | None = None,
        legend_parameter: dict[str, Any] | None = None,
        plot_irradiance: bool = False,
        show_components: bool = False,
        include_title: bool = True,
        azimuth_count: int = 72,
        altitude_count: int = 18,
        direction_count: int = 36,
        tilt_angle: float = 0.0,
        arrow_scale: float = 1.0,
        max_rad: float | None = None,
        # WindProfile inputs
        terrain: str = "city",
        meteorological_terrain: str = "country",
        meteorological_height: float = 10.0,
        log_law: bool = False,
        meteorological_wind_speed: float = 5.0,
        direction: float | None = None,
        max_height: float = 30.0,
        vector_spacing: float = 2.0,
        vector_length_dimension: float = 5.0,
        vector_height_dimension: float = 1.0,
        max_speed: float | None = None,
        scale_factor: float = 1.0,
        feet_labels: bool = False,
        # ViewSphere inputs
        view_type: str = "HorizontalRadial",
        resolution: int = 1,
        context_intersect_dist: list[float] | None = None,
        dist_units: str = "m",
        draw_view_rays: bool = True,
        # Compass inputs
        spacing_factor: float = 0.15,
        custom_angles: list[float] | None = None,
        font: str = "Arial",
        maj_txt_size: float | None = None,
        min_txt_size: float | None = None,
        # Shared spatial / output parameters
        radius: float = 100,
        center_point: dict[str, Any] | list[float] | None = None,
        projection: str | None = None,
        name: str | None = None,
        return_visualization_set: bool = True,
    ) -> dict[str, Any]:
        """Generate a Sunpath, SkyDome, RadiationDome, RadiationRose, WindProfile, ViewSphere, or Compass VisualizationSet."""
        coerced_legend = coerce_legend_parameter_dict(legend_parameter)
        coerced_legends = (
            [coerce_legend_parameter_dict(lp) for lp in legend_parameters]
            if legend_parameters
            else None
        )

        if sky_viz_type == "sunpath":
            return sunpath_to_visualization_set(
                garden_root=garden_root,
                location=location,
                weather_target=weather_target,
                epw_path=epw_path,
                north_angle=north_angle,
                hoys=hoys,
                data_collection_targets=data_collection_targets,
                data_collections=data_collections,
                legend_parameter=coerced_legend,
                legend_parameters=coerced_legends,
                radius=radius,
                center_point=center_point,
                solar_time=solar_time,
                daily=daily,
                projection=projection,
                sun_spheres=sun_spheres,
                name=name or "sunpath",
                return_visualization_set=return_visualization_set,
            )

        if sky_viz_type == "wind_profile":
            return wind_profile_to_visualization_set(
                garden_root=garden_root,
                terrain=terrain,
                meteorological_terrain=meteorological_terrain,
                meteorological_height=meteorological_height,
                log_law=log_law,
                meteorological_wind_speed=meteorological_wind_speed,
                direction=direction,
                legend_parameter=coerced_legend,
                center_point=center_point,
                max_height=max_height,
                vector_spacing=vector_spacing,
                vector_length_dimension=vector_length_dimension,
                vector_height_dimension=vector_height_dimension,
                max_speed=max_speed,
                scale_factor=scale_factor,
                feet_labels=feet_labels,
                name=name or "wind_profile",
                return_visualization_set=return_visualization_set,
            )

        if sky_viz_type == "view_sphere":
            return view_sphere_to_visualization_set(
                garden_root=garden_root,
                view_type=view_type,
                resolution=resolution,
                center_point=center_point,
                context_intersect_dist=context_intersect_dist,
                dist_units=dist_units,
                radius=radius if radius != 100 else 1.0,
                legend_parameter=coerced_legend,
                draw_view_rays=draw_view_rays,
                name=name or "view_sphere",
                return_visualization_set=return_visualization_set,
            )

        if sky_viz_type == "compass":
            return compass_to_visualization_set(
                garden_root=garden_root,
                radius=radius,
                center_point=center_point,
                north_angle=north_angle,
                spacing_factor=spacing_factor,
                custom_angles=custom_angles,
                projection=projection,
                font=font,
                maj_txt_size=maj_txt_size,
                min_txt_size=min_txt_size,
                name=name or "compass",
                return_visualization_set=return_visualization_set,
            )

        if sky_matrix_target is None:
            raise ValueError(
                f"sky_matrix_target is required for sky_viz_type={sky_viz_type!r}."
            )

        if sky_viz_type == "skydome":
            return sky_matrix_to_skydome_visualization_set(
                garden_root=garden_root,
                sky_matrix_target=sky_matrix_target,
                legend_parameter=coerced_legend,
                plot_irradiance=plot_irradiance,
                radius=radius,
                center_point=center_point,
                projection=projection,
                show_components=show_components,
                include_title=include_title,
                name=name or "sky_dome",
                return_visualization_set=return_visualization_set,
            )

        if sky_viz_type == "radiation_rose":
            return sky_matrix_to_radiation_rose_visualization_set(
                garden_root=garden_root,
                sky_matrix_target=sky_matrix_target,
                model_target=model_target,
                direction_count=direction_count,
                tilt_angle=tilt_angle,
                arrow_scale=arrow_scale,
                max_rad=max_rad,
                legend_parameter=coerced_legend,
                plot_irradiance=plot_irradiance,
                radius=radius,
                center_point=center_point,
                show_components=show_components,
                include_title=include_title,
                name=name or "radiation_rose",
                return_visualization_set=return_visualization_set,
            )

        return sky_matrix_to_radiation_dome_visualization_set(
            garden_root=garden_root,
            sky_matrix_target=sky_matrix_target,
            model_target=model_target,
            azimuth_count=azimuth_count,
            altitude_count=altitude_count,
            legend_parameter=coerced_legend,
            plot_irradiance=plot_irradiance,
            radius=radius,
            center_point=center_point,
            projection=projection,
            show_components=show_components,
            include_title=include_title,
            name=name or "radiation_dome",
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Compose_Visualization_Sets",
        tags={"ladybug", "visualization", "visualization-set", "compose", "overlay", "target"},
        timeout=30,
    )
    def LB_Compose_Visualization_Sets(
        visualization_sets: list[dict[str, Any]] | None = None,
        garden_root: str | None = None,
        visualization_set_targets: list[dict[str, Any]] | None = None,
        model_context_target: dict[str, Any] | None = None,
        analysis_visualization_set_target: dict[str, Any] | None = None,
        exclude_context_geometry_identifiers: list[str] | None = None,
        name: str | None = None,
        units: str | None = None,
        check_duplicate_geometry_ids: bool = True,
        conflict_strategy: Literal["error", "rename", "overwrite", "skip"] | None = None,
        return_visualization_set: bool = True,
    ) -> dict[str, Any]:
        """Compose VisualizationSets or overlay an analysis layer onto a model-context set."""
        if (model_context_target is not None) != (
            analysis_visualization_set_target is not None
        ):
            raise ValueError(
                "Both model_context_target and analysis_visualization_set_target are required for model-analysis overlay."
            )
        if (
            model_context_target is not None
            and analysis_visualization_set_target is not None
        ):
            root = _require_garden_root(
                garden_root, "model-analysis VisualizationSet overlay"
            )
            return compose_model_analysis_visualization_set(
                garden_root=root,
                model_context_target=model_context_target,
                analysis_visualization_set_target=analysis_visualization_set_target,
                name=name or "model_analysis_overlay",
                units=units,
                exclude_context_geometry_identifiers=exclude_context_geometry_identifiers,
                conflict_strategy=conflict_strategy or "rename",
                return_visualization_set=return_visualization_set,
            )
        return compose_visualization_sets(
            visualization_sets=visualization_sets,
            garden_root=garden_root,
            visualization_set_targets=visualization_set_targets,
            name=name,
            units=units,
            check_duplicate_geometry_ids=check_duplicate_geometry_ids,
            conflict_strategy=conflict_strategy or "error",
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="LB_Export_Visualization_Set",
        tags={"ladybug", "visualization", "visualization-set", "export", "html", "svg", "vtkjs", "artifact"},
        timeout=60,
    )
    def LB_Export_Visualization_Set(
        garden_root: str,
        export_format: Literal["html", "svg", "vtkjs", "png", "vtk", "vtp", "vsf", "pkl"],
        visualization_set: dict[str, Any] | None = None,
        visualization_set_target: dict[str, Any] | None = None,
        name: str = "visualization_set",
        output_subdir: str | None = None,
        open: bool = False,
        width: int = 1600,
        height: int = 900,
        view: str | dict[str, Any] = "Top",
        margin: float | None = None,
        interactive: bool = False,
        render_2d_legend: bool = True,
        render_3d_legend: bool = False,
    ) -> dict[str, Any]:
        """Export a VisualizationSet dictionary or Garden target to HTML, SVG, VTKJS, PNG, VTK, VTP, VSF, or PKL."""
        return export_visualization_set(
            garden_root=garden_root,
            export_format=export_format,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
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
        )

    @mcp.tool(
        name="LB_Data_Collection_To_File",
        tags={"ladybug", "data-collection", "export", "json", "csv", "pkl", "artifact"},
        timeout=30,
    )
    def LB_Data_Collection_To_File(
        garden_root: str,
        data_collection: dict[str, Any] | None = None,
        data_collection_target: dict[str, Any] | None = None,
        data_collections: list[dict[str, Any]] | None = None,
        data_collection_targets: list[dict[str, Any]] | None = None,
        file_format: Literal["json", "csv", "pkl"] = "json",
        name: str = "data_collection",
        output_subdir: str = "artifacts/data_collections",
    ) -> dict[str, Any]:
        """Export one or more Ladybug DataCollection dicts or targets to a JSON, CSV, or PKL artifact."""
        return export_data_collection_file(
            garden_root=garden_root,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            data_collections=data_collections,
            data_collection_targets=data_collection_targets,
            file_format=file_format,
            name=name,
            output_subdir=output_subdir,
            source={"producer": "LB_Data_Collection_To_File"},
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
        garden_root: str,
        study_type: Literal[
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
        study_mesh: dict[str, Any] | None = None,
        study_face: dict[str, Any] | None = None,
        context_geometry: list[dict[str, Any]] | None = None,
        model_target: dict[str, Any] | None = None,
        study_face_targets: list[dict[str, Any]] | None = None,
        study_room_targets: list[dict[str, Any]] | None = None,
        face_type_filter: str | None = None,
        grid_size: float | None = None,
        vectors: list[list[float] | dict[str, Any]] | None = None,
        sky_matrix_target: dict[str, Any] | None = None,
        weather_target: dict[str, Any] | None = None,
        epw_path: str | None = None,
        location: dict[str, Any] | None = None,
        hoys: list[float] | None = None,
        analysis_period: dict[str, Any] | str | None = None,
        north_angle: float = 0.0,
        solar_time: bool = False,
        timestep: int = 1,
        high_density: bool = False,
        ground_reflectance: float = 0.2,
        benefit: bool = False,
        balance_temperature: float = 15.0,
        balance_offset: float = 2.0,
        plot_irradiance: bool = False,
        offset_distance: float = 0.0,
        by_vertex: bool = False,
        use_radiance_mesh: bool = False,
        height_limit: float = 100.0,
        solar_rights: bool = False,
        view_type: str = "SkyExposure",
        resolution: int = 1,
        center_point: list[float] | dict[str, Any] | None = None,
        radius: float = 5.0,
        numericalize: bool = False,
        geo_block: bool | None = None,
        include_view_rose: bool = False,
        draw_view_rays: bool = True,
        shade_geometry: list[dict[str, Any]] | None = None,
        study_region: list[dict[str, Any]] | None = None,
        study_points: list[list[float] | dict[str, Any]] | None = None,
        study_directions: list[list[float] | dict[str, Any]] | None = None,
        temperature_target: dict[str, Any] | None = None,
        up_threshold: float = 26.0,
        low_threshold: float = 9.0,
        source_geometry: list[dict[str, Any]] | None = None,
        receiver_geometry: list[dict[str, Any]] | None = None,
        bounce_count: int = 1,
        first_length: float | None = None,
        last_length: float | None = None,
        context_block: bool = False,
        legend_parameter: dict[str, Any] | None = None,
        include_title: bool = True,
        include_context: bool = True,
        include_values: bool = False,
        name: str | None = None,
        return_visualization_set: bool = True,
    ) -> dict[str, Any]:
        """Run DirectSunStudy, RadiationStudy, SolarEnvelope, SkyIntersection, ViewSphere, ShadeBenefit, ThermalShadeBenefit, SurfaceRayTracing, ViewPercent, or ViewRose study."""
        return run_solar_geometry_study(
            garden_root=garden_root,
            study_type=study_type,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            vectors=vectors,
            sky_matrix_target=sky_matrix_target,
            weather_target=weather_target,
            epw_path=epw_path,
            location=location,
            hoys=hoys,
            analysis_period=analysis_period,
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
            center_point=center_point,
            radius=radius,
            numericalize=numericalize,
            geo_block=geo_block,
            include_view_rose=include_view_rose,
            draw_view_rays=draw_view_rays,
            shade_geometry=shade_geometry,
            study_region=study_region,
            study_points=study_points,
            study_directions=study_directions,
            temperature_target=temperature_target,
            up_threshold=up_threshold,
            low_threshold=low_threshold,
            source_geometry=source_geometry,
            receiver_geometry=receiver_geometry,
            bounce_count=bounce_count,
            first_length=first_length,
            last_length=last_length,
            context_block=context_block,
            legend_parameter=coerce_legend_parameter_dict(legend_parameter),
            include_title=include_title,
            include_context=include_context,
            include_values=include_values,
            name=name,
            return_visualization_set=return_visualization_set,
        )
