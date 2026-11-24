"""Garden-backed Ladybug psychrometric and adaptive chart visualization services."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Any

from ladybug.color import Color
from ladybug.datatype.fraction import RelativeHumidity
from ladybug.datatype.temperature import Temperature
from ladybug.legend import LegendParameters
from ladybug.psychchart import PsychrometricChart
from ladybug_comfort.chart.adaptive import AdaptiveChart
from ladybug_comfort.chart.polygonpmv import PolygonPMV
from ladybug_comfort.chart.polygonutci import PolygonUTCI
from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.parameter.pmv import PMVParameter
from ladybug_comfort.parameter.utci import UTCIParameter
from ladybug_display.extension.adaptivechart import adaptive_chart_to_vis_set
from ladybug_display.extension.psychchart import psychrometric_chart_to_vis_set
from ladybug_display.geometry3d import DisplayLineSegment3D, DisplayPolyline3D
from ladybug_display.visualization import ContextGeometry
from ladybug_geometry.geometry2d import LineSegment2D, Point2D, Polyline2D
from ladybug_geometry.geometry3d import LineSegment3D, Plane, Point3D, Polyline3D

from garden.data_collection import (
    DATA_COLLECTION_TARGET_TYPE,
    data_collection_summary,
    load_data_collection,
)
from garden.manifest import GardenManifest
from garden.passive_strategy import (
    PassiveStrategyParameters,
    evaluate_pmv_passive_strategies,
    evaluate_utci_polygons,
    normalize_passive_strategies,
    summarize_polygon_numeric_input,
)
from garden.paths import slugify_name
from garden.visualize.artifacts import coerce_legend_parameter, save_visualization_set
from garden.visualize.legend import legend_parameter_from_dict
from ladybug_tools_mcp.contracts import make_report


def _load_collection(
    *,
    garden_root: str | Path,
    target: dict[str, Any] | None,
    field_name: str,
) -> Any:
    if not isinstance(target, dict):
        raise ValueError(f"{field_name} must be a ladybug_data_collection target.")
    if target.get("target_type") != DATA_COLLECTION_TARGET_TYPE:
        raise ValueError(
            f"{field_name}.target_type must be {DATA_COLLECTION_TARGET_TYPE!r}."
        )
    try:
        collection = load_data_collection(
            garden_root=garden_root,
            data_collection_target=target,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not load {field_name}: {exc}") from exc
    if not getattr(collection, "values", None):
        raise ValueError(f"{field_name} must contain at least one value.")
    _numeric_values(collection, field_name=field_name)
    return collection


def _numeric_values(
    collection: Any,
    *,
    field_name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> list[float]:
    values: list[float] = []
    for index, value in enumerate(getattr(collection, "values", ())):
        if isinstance(value, bool):
            raise ValueError(f"{field_name}.values[{index}] must be numeric.")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name}.values[{index}] must be numeric.") from exc
        if not isfinite(number):
            raise ValueError(f"{field_name}.values[{index}] must be finite.")
        if minimum is not None and number < minimum:
            raise ValueError(
                f"{field_name}.values[{index}] must be at least {minimum}."
            )
        if maximum is not None and number > maximum:
            raise ValueError(
                f"{field_name}.values[{index}] must be at most {maximum}."
            )
        values.append(number)
    return values


def _point2d(value: dict[str, Any] | list[float] | tuple[float, ...] | None) -> Point2D:
    if value is None:
        return Point2D()
    if isinstance(value, dict):
        try:
            x = float(value["x"])
            y = float(value["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("base_point must include numeric x and y values.") from exc
        if not isfinite(x) or not isfinite(y):
            raise ValueError("base_point must include finite x and y values.")
        return Point2D(x, y)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            x = float(value[0])
            y = float(value[1])
        except (TypeError, ValueError) as exc:
            raise ValueError("base_point must contain numeric x and y values.") from exc
        if not isfinite(x) or not isfinite(y):
            raise ValueError("base_point must contain finite x and y values.")
        return Point2D(x, y)
    raise ValueError("base_point must be a dict with x/y or a 2-item list.")


def _positive_number(value: float | int, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive number.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{field_name} must be a finite number greater than 0.")
    return number


def _legend_parameter(data: dict[str, Any] | None) -> Any:
    if data is None:
        return None
    try:
        return coerce_legend_parameter(data)
    except (TypeError, ValueError, AssertionError) as exc:
        raise ValueError(f"Invalid legend_parameter: {exc}") from exc


def _strategy_layers(
    *,
    garden_root: str | Path,
    layers: list[dict[str, Any]] | None,
    collection_length: int,
) -> tuple[list[Any], list[LegendParameters], list[dict[str, Any]]]:
    if layers is None:
        return [], [], []
    if not isinstance(layers, list):
        raise ValueError("strategy_layers must be a list of layer dictionaries.")

    collections: list[Any] = []
    legends: list[LegendParameters] = []
    summaries: list[dict[str, Any]] = []
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError(f"strategy_layers[{index}] must be a dictionary.")
        target = layer.get("data_collection_target")
        if target is None and layer.get("target_type") == DATA_COLLECTION_TARGET_TYPE:
            target = layer
        collection = _load_collection(
            garden_root=garden_root,
            target=target,
            field_name=f"strategy_layers[{index}].data_collection_target",
        )
        if len(collection) != collection_length:
            raise ValueError(
                f"strategy_layers[{index}] must contain {collection_length} values; "
                f"got {len(collection)}."
            )

        label = str(
            layer.get("label")
            or (target or {}).get("identifier")
            or f"Strategy {index + 1}"
        ).strip()
        if not label:
            raise ValueError(f"strategy_layers[{index}].label cannot be empty.")
        legend = _legend_parameter(layer.get("legend_parameter"))
        if legend is None:
            legend = LegendParameters(title=label)
        elif getattr(legend, "is_title_default", False) or not legend.title:
            legend.title = label

        collections.append(collection)
        legends.append(legend)
        summaries.append(
            {
                "label": label,
                "data_collection_target": target,
                "data_collection": data_collection_summary(collection),
                "legend_parameter": legend.to_dict(),
            }
        )
    return collections, legends, summaries


def _visualization_set_summary(visualization_set: dict[str, Any]) -> dict[str, Any]:
    geometry = visualization_set.get("geometry", []) or []
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "geometry_count": len(geometry),
        "geometry_identifiers": [
            item.get("identifier")
            for item in geometry
            if isinstance(item, dict) and item.get("identifier")
        ],
    }


def _polygon_segments_to_display(
    segments: tuple[Any, ...] | list[Any],
    *,
    z_value: float,
    color: Color,
    line_width: int = 2,
) -> list[Any]:
    bp = Plane(o=Point3D(0, 0, z_value))
    display_objs: list[Any] = []
    for seg in segments:
        if isinstance(seg, Polyline2D):
            pl3 = Polyline3D.from_polyline2d(seg, bp)
            display_objs.append(DisplayPolyline3D(pl3, color=color, line_width=line_width))
        elif isinstance(seg, LineSegment2D):
            ls3 = LineSegment3D.from_line_segment2d(seg, z_value)
            display_objs.append(DisplayLineSegment3D(ls3, color=color, line_width=line_width))
    return display_objs


_PMV_STRATEGY_OVERLAY_META: dict[str, tuple[str, Color]] = {
    "evaporative_cooling": ("Evaporative_Cooling_Polygon", Color(0, 130, 210)),
    "fan_use": ("Fan_Use_Polygon", Color(30, 180, 180)),
    "night_flush": ("Night_Flush_Polygon", Color(80, 90, 200)),
    "internal_heat": ("Internal_Heat_Polygon", Color(210, 140, 40)),
    "passive_solar": ("Passive_Solar_Polygon", Color(225, 195, 30)),
    "shade_line": ("Shade_Line", Color(110, 110, 110)),
}

_UTCI_STRESS_COLORS: dict[str, Color] = {
    "moderate_cold": Color(100, 170, 230),
    "strong_cold": Color(40, 100, 210),
    "very_strong_cold": Color(15, 45, 160),
    "moderate_heat": Color(240, 170, 50),
    "strong_heat": Color(230, 95, 25),
    "very_strong_heat": Color(180, 20, 20),
}


def _resolve_polygon_numeric_or_seq(
    *,
    garden_root_path: Path,
    value: Any,
    field_name: str,
) -> list[float] | None:
    return summarize_polygon_numeric_input(
        value,
        load_collection_fn=lambda tgt, fn: _load_collection(
            garden_root=garden_root_path, target=tgt, field_name=fn
        ),
        field_name=field_name,
    )


def _merge_passive_strategy_params(
    *,
    comfort_polygon: dict[str, Any] | None,
    passive_strategy_parameters: dict[str, Any] | None,
) -> PassiveStrategyParameters:
    merged: dict[str, Any] = {}
    if comfort_polygon:
        for src_key in (
            "day_above_comfort",
            "day_above_comf",
            "night_flush_temp_above_comfort",
            "temperature_above_comfort",
            "night_below_comfort",
            "night_below_comf",
            "fan_air_speed",
            "balance_temperature",
            "balance_temp",
            "internal_heat_balance_temperature",
            "solar_heat_capacity",
            "solar_heat_cap",
            "time_constant",
        ):
            if comfort_polygon.get(src_key) is not None:
                merged[src_key] = comfort_polygon[src_key]
        if isinstance(comfort_polygon.get("passive_strategy_parameters"), dict):
            merged.update(comfort_polygon["passive_strategy_parameters"])
    if passive_strategy_parameters:
        merged.update(passive_strategy_parameters)
    return PassiveStrategyParameters.from_dict(merged or None)


def _overlay_pmv_and_strategies(
    *,
    vis_set: Any,
    chart: PsychrometricChart,
    garden_root_path: Path,
    spec: dict[str, Any],
    params: PassiveStrategyParameters,
    strategies_input: Any,
    incident_irradiance_target: dict[str, Any] | None,
    outdoor_temperature_target: dict[str, Any] | None,
    mean_radiant_temperature_target: dict[str, Any] | None,
    air_speed_target: dict[str, Any] | None,
    comfort_parameter: dict[str, Any] | None,
    z_value: float,
    comfort_prefix: str = "Comfort_Polygon",
    draw_geometry: bool = True,
) -> dict[str, Any]:
    rad_val = spec.get("rad_temperature") or spec.get("mean_radiant_temperature_target") or mean_radiant_temperature_target
    rad_temp = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=rad_val,
        field_name="comfort_polygon.rad_temperature",
    )
    air_val = spec.get("air_speed") or spec.get("air_speed_target") or air_speed_target
    air_speed = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=air_val,
        field_name="comfort_polygon.air_speed",
    )
    met_rate = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=spec.get("met_rate"),
        field_name="comfort_polygon.met_rate",
    )
    clo_value = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=spec.get("clo_value"),
        field_name="comfort_polygon.clo_value",
    )
    external_work = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=spec.get("external_work"),
        field_name="comfort_polygon.external_work",
    )
    pmv_par = None
    raw_par = spec.get("comfort_parameter") or (
        comfort_parameter
        if (comfort_parameter and comfort_parameter.get("type") in {None, "PMVParameter"})
        else None
    )
    if raw_par:
        p_data = dict(raw_par)
        p_data.setdefault("type", "PMVParameter")
        pmv_par = PMVParameter.from_dict(p_data)

    ppmv = PolygonPMV(
        chart,
        rad_temperature=rad_temp,
        air_speed=air_speed,
        met_rate=met_rate,
        clo_value=clo_value,
        external_work=external_work,
        comfort_parameter=pmv_par,
    )

    irr_target = spec.get("incident_irradiance_target") or incident_irradiance_target
    irr_col = (
        _load_collection(
            garden_root=garden_root_path,
            target=irr_target,
            field_name="incident_irradiance_target",
        )
        if irr_target is not None
        else None
    )
    out_target = spec.get("outdoor_temperature_target") or outdoor_temperature_target
    out_col = (
        _load_collection(
            garden_root=garden_root_path,
            target=out_target,
            field_name="outdoor_temperature_target",
        )
        if out_target is not None
        else None
    )

    enabled = normalize_passive_strategies(
        strategies_input,
        has_solar=(irr_col is not None),
        strict=False,
    )
    if spec.get("shade_balance_temperature") is not None and "shade_line" not in enabled:
        enabled.append("shade_line")

    merge_polygons = bool(spec.get("merge_polygons", True))
    bal_raw = spec.get("passive_solar_balance_temperature")
    bal_val = float(bal_raw) if bal_raw is not None else None
    shade_bal_raw = spec.get("shade_balance_temperature")
    shade_bal_val = float(shade_bal_raw) if shade_bal_raw is not None else None

    eval_res = evaluate_pmv_passive_strategies(
        chart=chart,
        ppmv=ppmv,
        params=params,
        strategies=enabled,
        outdoor_temperature=out_col,
        incident_irradiance=irr_col,
        passive_solar_balance_temperature=bal_val,
        passive_solar_max_delta=float(spec.get("passive_solar_max_delta", 10.0)),
        shade_balance_temperature=shade_bal_val,
        merge_polygons=merge_polygons,
    )

    if draw_geometry:
        geos = eval_res["polygon_geometries"]
        comfort_polys = geos["comfort_polygons"]
        if len(comfort_polys) == 1:
            vis_set.add_geometry(
                ContextGeometry(
                    comfort_prefix,
                    _polygon_segments_to_display(
                        comfort_polys[0],
                        z_value=z_value,
                        color=Color(0, 150, 100),
                        line_width=3,
                    ),
                )
            )
        else:
            for idx, poly in enumerate(comfort_polys, start=1):
                vis_set.add_geometry(
                    ContextGeometry(
                        f"{comfort_prefix}_{idx}",
                        _polygon_segments_to_display(
                            poly,
                            z_value=z_value,
                            color=Color(0, 150, 100),
                            line_width=2,
                        ),
                    )
                )
        for strat_key in eval_res["statistics"]["strategies_added"]:
            segs = geos.get(strat_key)
            if segs:
                layer_id, layer_color = _PMV_STRATEGY_OVERLAY_META[strat_key]
                vis_set.add_geometry(
                    ContextGeometry(
                        layer_id,
                        _polygon_segments_to_display(segs, z_value=z_value, color=layer_color),
                    )
                )

    return eval_res["statistics"]


def _overlay_utci_polygons(
    *,
    vis_set: Any,
    chart: PsychrometricChart,
    garden_root_path: Path,
    spec: dict[str, Any],
    mean_radiant_temperature_target: dict[str, Any] | None,
    wind_speed_target: dict[str, Any] | None,
    comfort_parameter: dict[str, Any] | None,
    z_value: float,
    comfort_prefix: str = "Comfort_Polygon",
    draw_geometry: bool = True,
) -> dict[str, Any]:
    rad_val = spec.get("rad_temperature") or spec.get("mean_radiant_temperature_target") or mean_radiant_temperature_target
    rad_temp = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=rad_val,
        field_name="comfort_polygon.rad_temperature",
    )
    wind_val = spec.get("wind_speed") or spec.get("wind_speed_target") or wind_speed_target
    wind_speed = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=wind_val,
        field_name="comfort_polygon.wind_speed",
    )
    utci_par = None
    raw_par = spec.get("comfort_parameter") or (
        comfort_parameter
        if (comfort_parameter and comfort_parameter.get("type") in {None, "UTCIParameter"})
        else None
    )
    if raw_par:
        p_data = dict(raw_par)
        p_data.setdefault("type", "UTCIParameter")
        utci_par = UTCIParameter.from_dict(p_data)

    putci = PolygonUTCI(
        chart,
        rad_temperature=rad_temp,
        wind_speed=wind_speed,
        comfort_parameter=utci_par,
    )
    stress_spec = spec.get("stress_polygons")
    if stress_spec is None and spec.get("plot_stress") is not None:
        stress_spec = bool(spec.get("plot_stress"))
    merge_polygons = bool(spec.get("merge_polygons", True))

    eval_res = evaluate_utci_polygons(
        putci,
        merge_polygons=merge_polygons,
        stress_polygons=stress_spec,
    )
    if draw_geometry:
        comfort_polys = eval_res["comfort_polygons"]
        if len(comfort_polys) == 1:
            vis_set.add_geometry(
                ContextGeometry(
                    comfort_prefix,
                    _polygon_segments_to_display(
                        comfort_polys[0],
                        z_value=z_value,
                        color=Color(0, 150, 100),
                        line_width=3,
                    ),
                )
            )
        else:
            for idx, poly in enumerate(comfort_polys, start=1):
                vis_set.add_geometry(
                    ContextGeometry(
                        f"{comfort_prefix}_{idx}",
                        _polygon_segments_to_display(
                            poly,
                            z_value=z_value,
                            color=Color(0, 150, 100),
                            line_width=2,
                        ),
                    )
                )
        for s_name, segs in eval_res["stress_geometries"].items():
            vis_set.add_geometry(
                ContextGeometry(
                    f"UTCI_{s_name}",
                    _polygon_segments_to_display(
                        segs,
                        z_value=z_value,
                        color=_UTCI_STRESS_COLORS.get(s_name, Color(120, 120, 120)),
                        line_width=2,
                    ),
                )
            )
    return eval_res["statistics"]


def _apply_comfort_polygon(
    *,
    vis_set: Any,
    chart: PsychrometricChart,
    garden_root_path: Path,
    comfort_polygon: dict[str, Any] | None,
    include_passive_strategies: bool,
    passive_strategy_parameters: dict[str, Any] | None,
    passive_strategies: list[str] | None,
    incident_irradiance_target: dict[str, Any] | None,
    outdoor_temperature_target: dict[str, Any] | None,
    mean_radiant_temperature_target: dict[str, Any] | None,
    air_speed_target: dict[str, Any] | None,
    wind_speed_target: dict[str, Any] | None,
    comfort_parameter: dict[str, Any] | None,
    z_value: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if comfort_polygon is None and not include_passive_strategies:
        return None, None

    spec = dict(comfort_polygon or {})
    poly_model = str(spec.get("model") or spec.get("type") or "pmv").strip().lower()
    if poly_model not in {"pmv", "utci", "both"}:
        raise ValueError("comfort_polygon.model must be 'pmv', 'utci', or 'both'.")

    params = _merge_passive_strategy_params(
        comfort_polygon=spec,
        passive_strategy_parameters=passive_strategy_parameters,
    )
    strategies_input = (
        spec.get("strategies")
        if spec.get("strategies") is not None
        else passive_strategies
    )

    if poly_model == "pmv":
        pmv_stats = _overlay_pmv_and_strategies(
            vis_set=vis_set,
            chart=chart,
            garden_root_path=garden_root_path,
            spec=spec,
            params=params,
            strategies_input=strategies_input,
            incident_irradiance_target=incident_irradiance_target,
            outdoor_temperature_target=outdoor_temperature_target,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            air_speed_target=air_speed_target,
            comfort_parameter=comfort_parameter,
            z_value=z_value,
            comfort_prefix="Comfort_Polygon",
            draw_geometry=True,
        )
        return pmv_stats, pmv_stats

    if poly_model == "utci":
        utci_stats = _overlay_utci_polygons(
            vis_set=vis_set,
            chart=chart,
            garden_root_path=garden_root_path,
            spec=spec,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            wind_speed_target=wind_speed_target,
            comfort_parameter=comfort_parameter,
            z_value=z_value,
            comfort_prefix="Comfort_Polygon",
            draw_geometry=True,
        )
        passive_stats = None
        if include_passive_strategies:
            passive_stats = _overlay_pmv_and_strategies(
                vis_set=vis_set,
                chart=chart,
                garden_root_path=garden_root_path,
                spec=spec,
                params=params,
                strategies_input=strategies_input,
                incident_irradiance_target=incident_irradiance_target,
                outdoor_temperature_target=outdoor_temperature_target,
                mean_radiant_temperature_target=mean_radiant_temperature_target,
                air_speed_target=air_speed_target,
                comfort_parameter=None,
                z_value=z_value,
                draw_geometry=False,
            )
        return utci_stats, passive_stats

    # poly_model == "both"
    pmv_stats = _overlay_pmv_and_strategies(
        vis_set=vis_set,
        chart=chart,
        garden_root_path=garden_root_path,
        spec=spec,
        params=params,
        strategies_input=strategies_input,
        incident_irradiance_target=incident_irradiance_target,
        outdoor_temperature_target=outdoor_temperature_target,
        mean_radiant_temperature_target=mean_radiant_temperature_target,
        air_speed_target=air_speed_target,
        comfort_parameter=comfort_parameter,
        z_value=z_value,
        comfort_prefix="PMV_Comfort_Polygon",
        draw_geometry=True,
    )
    utci_stats = _overlay_utci_polygons(
        vis_set=vis_set,
        chart=chart,
        garden_root_path=garden_root_path,
        spec=spec,
        mean_radiant_temperature_target=mean_radiant_temperature_target,
        wind_speed_target=wind_speed_target,
        comfort_parameter=comfort_parameter,
        z_value=z_value,
        comfort_prefix="UTCI_Comfort_Polygon",
        draw_geometry=True,
    )
    combined = {
        "model": "both",
        "pmv": pmv_stats,
        "utci": utci_stats,
    }
    return combined, pmv_stats


def psychrometric_chart_to_visualization_set(
    *,
    garden_root: str,
    temperature_target: dict[str, Any],
    relative_humidity_target: dict[str, Any],
    strategy_layers: list[dict[str, Any]] | None = None,
    comfort_polygon: dict[str, Any] | None = None,
    include_passive_strategies: bool = True,
    passive_strategy_parameters: dict[str, Any] | None = None,
    passive_strategies: list[str] | None = None,
    incident_irradiance_target: dict[str, Any] | None = None,
    outdoor_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    average_pressure: float = 101325,
    legend_parameter: dict[str, Any] | None = None,
    base_point: dict[str, Any] | list[float] | tuple[float, ...] | None = None,
    x_dim: float = 1,
    y_dim: float = 1500,
    min_temperature: float = -20,
    max_temperature: float = 50,
    max_humidity_ratio: float = 0.03,
    use_ip: bool = False,
    z: float = 0,
    plot_wet_bulb: bool = False,
    name: str = "psychrometric_chart",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create and persist a psychrometric chart with optional strategy and comfort polygon layers."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    temperature = _load_collection(
        garden_root=garden_root_path,
        target=temperature_target,
        field_name="temperature_target",
    )
    relative_humidity = _load_collection(
        garden_root=garden_root_path,
        target=relative_humidity_target,
        field_name="relative_humidity_target",
    )
    _numeric_values(
        relative_humidity,
        field_name="relative_humidity_target",
        minimum=0,
        maximum=100,
    )
    if len(temperature) != len(relative_humidity):
        raise ValueError(
            "temperature_target and relative_humidity_target must contain the same "
            "number of values."
        )

    pressure = _positive_number(average_pressure, "average_pressure")
    chart_x_dim = _positive_number(x_dim, "x_dim")
    chart_y_dim = _positive_number(y_dim, "y_dim")
    humidity_ratio = _positive_number(max_humidity_ratio, "max_humidity_ratio")
    if humidity_ratio < 0.005:
        raise ValueError("max_humidity_ratio must be at least 0.005.")
    if isinstance(min_temperature, bool) or isinstance(max_temperature, bool):
        raise ValueError("min_temperature and max_temperature must be numbers.")
    try:
        min_temp = float(min_temperature)
        max_temp = float(max_temperature)
    except (TypeError, ValueError) as exc:
        raise ValueError("min_temperature and max_temperature must be numbers.") from exc
    if not isfinite(min_temp) or not isfinite(max_temp):
        raise ValueError("min_temperature and max_temperature must be finite numbers.")
    if max_temp - min_temp < 10:
        raise ValueError(
            "max_temperature and min_temperature must differ by at least 10."
        )
    try:
        chart = PsychrometricChart(
            temperature,
            relative_humidity,
            average_pressure=pressure,
            legend_parameters=_legend_parameter(legend_parameter),
            base_point=_point2d(base_point),
            x_dim=chart_x_dim,
            y_dim=chart_y_dim,
            min_temperature=min_temp,
            max_temperature=max_temp,
            max_humidity_ratio=humidity_ratio,
            use_ip=use_ip,
        )
    except (AssertionError, IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not create psychrometric chart: {exc}") from exc

    collections, legends, layer_summaries = _strategy_layers(
        garden_root=garden_root_path,
        layers=strategy_layers,
        collection_length=len(temperature),
    )
    if isinstance(z, bool):
        raise ValueError("z must be a finite number.")
    try:
        z_value = float(z)
    except (TypeError, ValueError) as exc:
        raise ValueError("z must be a finite number.") from exc
    if not isfinite(z_value):
        raise ValueError("z must be a finite number.")
    try:
        vis_set = psychrometric_chart_to_vis_set(
            chart,
            data=collections or None,
            legend_parameters=legends or None,
            z=z_value,
            plot_wet_bulb=plot_wet_bulb,
        )
    except (AssertionError, IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not render psychrometric chart: {exc}") from exc

    polygon_summary, passive_stats = _apply_comfort_polygon(
        vis_set=vis_set,
        chart=chart,
        garden_root_path=garden_root_path,
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
        z_value=z_value,
    )

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string.")
    safe_name = slugify_name(name)
    vis_set.identifier = safe_name
    vis_set.display_name = name
    visualization_set = vis_set.to_dict()
    source = {
        "producer": "psychrometric_chart_to_visualization_set",
        "temperature_target": temperature_target,
        "relative_humidity_target": relative_humidity_target,
        "strategy_layers": layer_summaries,
        "comfort_polygon": polygon_summary,
        "passive_strategy_statistics": passive_stats,
        "average_pressure": pressure,
        "legend_parameter": legend_parameter,
        "base_point": {"x": chart.base_point.x, "y": chart.base_point.y},
        "x_dim": chart_x_dim,
        "y_dim": chart_y_dim,
        "min_temperature": min_temp,
        "max_temperature": max_temp,
        "max_humidity_ratio": humidity_ratio,
        "use_ip": bool(use_ip),
        "z": z_value,
        "plot_wet_bulb": bool(plot_wet_bulb),
    }
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
    )
    summary_view = {
        "garden_target": manifest.target(),
        "source": source,
        "visualization_set": _visualization_set_summary(visualization_set),
        "visualization_set_target": saved["visualization_set_target"],
        "temperature": data_collection_summary(temperature),
        "relative_humidity": data_collection_summary(relative_humidity),
        "temperature_target": temperature_target,
        "relative_humidity_target": relative_humidity_target,
        "strategy_layers": layer_summaries,
        "comfort_polygon": polygon_summary,
        "passive_strategy_statistics": passive_stats,
        "chart": {
            "average_pressure": pressure,
            "base_point": {"x": chart.base_point.x, "y": chart.base_point.y},
            "x_dim": chart_x_dim,
            "y_dim": chart_y_dim,
            "min_temperature": chart.min_temperature,
            "max_temperature": chart.max_temperature,
            "max_humidity_ratio": chart.max_humidity_ratio,
            "use_ip": chart.use_ip,
            "plot_wet_bulb": bool(plot_wet_bulb),
        },
        "body_returned": bool(return_visualization_set),
    }
    result: dict[str, Any] = {
        "target": saved["target"],
        "visualization_set_target": saved["visualization_set_target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="Psychrometric chart VisualizationSet created.",
        ),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result


def _adaptive_band_segments(
    chart: AdaptiveChart,
    t_min_c: float,
    t_max_c: float,
) -> tuple[Polyline2D, float, float] | None:
    temp_type = Temperature()
    y_min_val, y_max_val = (
        temp_type.to_unit([t_min_c, t_max_c], "F", "C")
        if chart.use_ip
        else (t_min_c, t_max_c)
    )
    y_low = max(float(chart.min_operative), float(y_min_val))
    y_high = min(float(chart.max_operative), float(y_max_val))
    if y_high <= y_low:
        return None
    x_low = chart.tp_x_value(chart.min_prevailing)
    x_high = chart.tp_x_value(chart.max_prevailing)
    y_low_coord = chart.to_y_value(y_low)
    y_high_coord = chart.to_y_value(y_high)
    band = Polyline2D(
        (
            Point2D(x_low, y_low_coord),
            Point2D(x_high, y_low_coord),
            Point2D(x_high, y_high_coord),
            Point2D(x_low, y_high_coord),
            Point2D(x_low, y_low_coord),
        )
    )
    return band, y_low, y_high


def adaptive_chart_to_visualization_set(
    *,
    garden_root: str,
    outdoor_temperature_target: dict[str, Any],
    operative_temperature_target: dict[str, Any] | None = None,
    air_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    comfort_polygon: dict[str, Any] | None = None,
    include_passive_strategies: bool = True,
    passive_strategy_parameters: dict[str, Any] | None = None,
    passive_strategies: list[str] | None = None,
    incident_irradiance_target: dict[str, Any] | None = None,
    average_pressure: float = 101325,
    strategy_layers: list[dict[str, Any]] | None = None,
    legend_parameter: dict[str, Any] | None = None,
    base_point: dict[str, Any] | list[float] | tuple[float, ...] | None = None,
    x_dim: float = 1,
    y_dim: float = 1,
    min_prevailing: float = 10,
    max_prevailing: float = 33,
    min_operative: float = 14,
    max_operative: float = 40,
    use_ip: bool = False,
    z: float = 0,
    name: str = "adaptive_chart",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create and persist a Ladybug AdaptiveChart VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    outdoor_temp = _load_collection(
        garden_root=garden_root_path,
        target=outdoor_temperature_target,
        field_name="outdoor_temperature_target",
    )
    air_speed_col = (
        _load_collection(
            garden_root=garden_root_path,
            target=air_speed_target,
            field_name="air_speed_target",
        )
        if air_speed_target is not None
        else None
    )
    adaptive_air_speed = float(air_speed_col.average) if air_speed_col is not None else None
    adp_par = None
    if comfort_parameter is not None:
        raw_type = comfort_parameter.get("type")
        if raw_type in {None, "AdaptiveParameter"}:
            p_data = dict(comfort_parameter)
            p_data.setdefault("type", "AdaptiveParameter")
            adp_par = AdaptiveParameter.from_dict(p_data)

    chart_x_dim = _positive_number(x_dim, "x_dim")
    chart_y_dim = _positive_number(y_dim, "y_dim")
    if operative_temperature_target is not None:
        operative_temp = _load_collection(
            garden_root=garden_root_path,
            target=operative_temperature_target,
            field_name="operative_temperature_target",
        )
        chart = AdaptiveChart(
            outdoor_temp,
            operative_temp,
            air_speed=adaptive_air_speed,
            comfort_parameter=adp_par,
            legend_parameters=_legend_parameter(legend_parameter),
            base_point=_point2d(base_point),
            x_dim=chart_x_dim,
            y_dim=chart_y_dim,
            min_prevailing=float(min_prevailing),
            max_prevailing=float(max_prevailing),
            min_operative=float(min_operative),
            max_operative=float(max_operative),
            use_ip=bool(use_ip),
        )
    elif air_temperature_target is not None:
        air_temp = _load_collection(
            garden_root=garden_root_path,
            target=air_temperature_target,
            field_name="air_temperature_target",
        )
        rad_temp = (
            _load_collection(
                garden_root=garden_root_path,
                target=mean_radiant_temperature_target,
                field_name="mean_radiant_temperature_target",
            )
            if mean_radiant_temperature_target is not None
            else None
        )
        chart = AdaptiveChart.from_air_and_rad_temp(
            outdoor_temp,
            air_temp,
            rad_temperature=rad_temp,
            air_speed=adaptive_air_speed,
            comfort_parameter=adp_par,
            legend_parameters=_legend_parameter(legend_parameter),
            base_point=_point2d(base_point),
            x_dim=chart_x_dim,
            y_dim=chart_y_dim,
            min_prevailing=float(min_prevailing),
            max_prevailing=float(max_prevailing),
            min_operative=float(min_operative),
            max_operative=float(max_operative),
            use_ip=bool(use_ip),
        )
    else:
        raise ValueError(
            "AdaptiveChart requires operative_temperature_target or air_temperature_target."
        )

    collections, legends, layer_summaries = _strategy_layers(
        garden_root=garden_root_path,
        layers=strategy_layers,
        collection_length=len(chart.operative_temperature),
    )

    class _AdaptiveChartProxy:
        def __init__(self, inner: AdaptiveChart) -> None:
            self._inner = inner

        @property
        def neutral_polyline(self) -> Polyline2D:
            raw_np = self._inner.neutral_polyline
            if isinstance(raw_np, LineSegment2D):
                return Polyline2D((raw_np.p1, raw_np.midpoint, raw_np.p2))
            return raw_np

        def __getattr__(self, item: str) -> Any:
            return getattr(self._inner, item)

    vis_chart: Any = _AdaptiveChartProxy(chart) if isinstance(chart.neutral_polyline, LineSegment2D) else chart
    z_value = float(z)
    vis_set = adaptive_chart_to_vis_set(
        vis_chart,
        data=collections or None,
        legend_parameters=legends or None,
        z=z_value,
    )

    percentages = {
        "comfortable": float(chart.percent_comfortable),
        "uncomfortable": float(chart.percent_uncomfortable),
        "neutral": float(
            chart.percent_neutral
            if chart.percent_neutral is not None
            else chart._collection.percent_neutral
        ),
        "cold": float(
            chart.percent_cold
            if chart.percent_cold is not None
            else chart._collection.percent_cold
        ),
        "hot": float(
            chart.percent_hot
            if chart.percent_hot is not None
            else chart._collection.percent_hot
        ),
    }

    polygon_summary: dict[str, Any] | None = None
    passive_stats: dict[str, Any] | None = None
    if include_passive_strategies or comfort_polygon is not None:
        spec = dict(comfort_polygon or {})
        poly_model = str(spec.get("model") or spec.get("type") or "pmv").strip().lower()
        if poly_model not in {"pmv", "utci", "both"}:
            raise ValueError("comfort_polygon.model must be 'pmv', 'utci', or 'both'.")
        params = _merge_passive_strategy_params(
            comfort_polygon=spec,
            passive_strategy_parameters=passive_strategy_parameters,
        )

        # Elevated air-speed fan comfort polygon in native Adaptive coordinate space
        adaptive_fan_pct: float | None = None
        adaptive_fan_gain_pct: float | None = None
        if params.fan_air_speed > chart.air_speed:
            try:
                outdoor_si = (
                    outdoor_temp.to_si()
                    if getattr(outdoor_temp.header, "unit", "C") != "C"
                    else outdoor_temp
                )
                fan_chart = AdaptiveChart(
                    outdoor_si,
                    chart._collection.operative_temperature,
                    air_speed=params.fan_air_speed,
                    comfort_parameter=adp_par,
                    base_point=chart.base_point,
                    x_dim=chart_x_dim,
                    y_dim=chart_y_dim,
                    min_prevailing=float(min_prevailing),
                    max_prevailing=float(max_prevailing),
                    min_operative=float(min_operative),
                    max_operative=float(max_operative),
                    use_ip=bool(use_ip),
                )
                fan_poly = Polyline2D.from_polygon(fan_chart.comfort_polygon)
                vis_set.add_geometry(
                    ContextGeometry(
                        "Adaptive_Fan_Use_Polygon",
                        _polygon_segments_to_display(
                            (fan_poly,),
                            z_value=z_value,
                            color=Color(30, 180, 180),
                            line_width=2,
                        ),
                    )
                )
                adaptive_fan_pct = float(fan_chart.percent_comfortable)
                adaptive_fan_gain_pct = adaptive_fan_pct - percentages["comfortable"]
            except (AssertionError, TypeError, ValueError):
                pass

        # Helper PsychrometricChart for PassiveStrategyParameters & PMV/UTCI overlays
        op_si = chart._collection.operative_temperature
        if relative_humidity_target is not None:
            rh_col = _load_collection(
                garden_root=garden_root_path,
                target=relative_humidity_target,
                field_name="relative_humidity_target",
            )
            _numeric_values(rh_col, field_name="relative_humidity_target", minimum=0, maximum=100)
            if len(rh_col) != len(op_si):
                raise ValueError(
                    "relative_humidity_target must contain the same number of values as operative_temperature."
                )
            rh_source = "target"
        else:
            rh_col = op_si.get_aligned_collection([50.0] * len(op_si), RelativeHumidity(), "%")
            rh_source = "default_50pct"

        ref_rh = max(0.0, min(100.0, float(rh_col.average)))
        helper_chart = PsychrometricChart(
            op_si,
            rh_col,
            average_pressure=_positive_number(average_pressure, "average_pressure"),
        )
        irr_target = spec.get("incident_irradiance_target") or incident_irradiance_target
        irr_col = (
            _load_collection(
                garden_root=garden_root_path,
                target=irr_target,
                field_name="incident_irradiance_target",
            )
            if irr_target is not None
            else None
        )
        strategies_input = (
            spec.get("strategies")
            if spec.get("strategies") is not None
            else passive_strategies
        )
        enabled_strategies = normalize_passive_strategies(
            strategies_input,
            has_solar=(irr_col is not None),
            strict=False,
        )
        enabled_strategies = [s for s in enabled_strategies if s != "shade_line"]

        pmv_band_bounds: dict[str, float] | None = None
        utci_band_bounds: dict[str, float] | None = None
        pmv_stats: dict[str, Any] | None = None
        utci_stats: dict[str, Any] | None = None

        if poly_model in {"pmv", "both"} or include_passive_strategies:
            rad_temp = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("rad_temperature") or spec.get("mean_radiant_temperature_target") or mean_radiant_temperature_target,
                field_name="comfort_polygon.rad_temperature",
            )
            air_spd = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("air_speed") or spec.get("air_speed_target") or air_speed_target,
                field_name="comfort_polygon.air_speed",
            )
            met_rt = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("met_rate"),
                field_name="comfort_polygon.met_rate",
            )
            clo_v = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("clo_value"),
                field_name="comfort_polygon.clo_value",
            )
            wme_v = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("external_work"),
                field_name="comfort_polygon.external_work",
            )
            pmv_par = None
            raw_pmv_par = spec.get("comfort_parameter") or (
                comfort_parameter
                if (comfort_parameter and comfort_parameter.get("type") == "PMVParameter")
                else None
            )
            if raw_pmv_par:
                p_data = dict(raw_pmv_par)
                p_data.setdefault("type", "PMVParameter")
                pmv_par = PMVParameter.from_dict(p_data)

            ppmv = PolygonPMV(
                helper_chart,
                rad_temperature=rad_temp,
                air_speed=air_spd,
                met_rate=met_rt,
                clo_value=clo_v,
                external_work=wme_v,
                comfort_parameter=pmv_par,
            )
            outdoor_si = (
                outdoor_temp.to_si()
                if getattr(outdoor_temp.header, "unit", "C") != "C"
                else outdoor_temp
            )
            eval_res = evaluate_pmv_passive_strategies(
                chart=helper_chart,
                ppmv=ppmv,
                params=params,
                strategies=enabled_strategies,
                outdoor_temperature=outdoor_si,
                incident_irradiance=irr_col,
                passive_solar_balance_temperature=(
                    float(spec["passive_solar_balance_temperature"])
                    if spec.get("passive_solar_balance_temperature") is not None
                    else None
                ),
                passive_solar_max_delta=float(spec.get("passive_solar_max_delta", 10.0)),
                merge_polygons=bool(spec.get("merge_polygons", True)),
            )
            pmv_stats = dict(eval_res["statistics"])
            pmv_stats["relative_humidity_source"] = rh_source
            pmv_stats["adaptive_fan_comfort_percent"] = adaptive_fan_pct
            pmv_stats["adaptive_fan_gain_percent"] = adaptive_fan_gain_pct
            passive_stats = pmv_stats

            if poly_model in {"pmv", "both"}:
                t_pairs = [
                    ppmv.max_min_air_temperatures(idx, [ref_rh])[0]
                    for idx in range(ppmv.polygon_count)
                ]
                t_low_c = min(p[0] for p in t_pairs)
                t_high_c = max(p[1] for p in t_pairs)
                band_res = _adaptive_band_segments(chart, t_low_c, t_high_c)
                if band_res is not None:
                    band_poly, y_low, y_high = band_res
                    vis_set.add_geometry(
                        ContextGeometry(
                            "PMV_Comfort_Polygon",
                            _polygon_segments_to_display(
                                (band_poly,),
                                z_value=z_value,
                                color=Color(0, 150, 100),
                                line_width=2,
                            ),
                        )
                    )
                    pmv_band_bounds = {
                        "operative_min": y_low,
                        "operative_max": y_high,
                        "reference_relative_humidity": ref_rh,
                    }

        if poly_model in {"utci", "both"}:
            rad_temp = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("rad_temperature") or spec.get("mean_radiant_temperature_target") or mean_radiant_temperature_target,
                field_name="comfort_polygon.rad_temperature",
            )
            wind_spd = _resolve_polygon_numeric_or_seq(
                garden_root_path=garden_root_path,
                value=spec.get("wind_speed") or spec.get("wind_speed_target") or wind_speed_target,
                field_name="comfort_polygon.wind_speed",
            )
            utci_par = None
            raw_utci_par = spec.get("comfort_parameter") or (
                comfort_parameter
                if (comfort_parameter and comfort_parameter.get("type") == "UTCIParameter")
                else None
            )
            if raw_utci_par:
                p_data = dict(raw_utci_par)
                p_data.setdefault("type", "UTCIParameter")
                utci_par = UTCIParameter.from_dict(p_data)

            putci = PolygonUTCI(
                helper_chart,
                rad_temperature=rad_temp,
                wind_speed=wind_spd,
                comfort_parameter=utci_par,
            )
            utci_eval = evaluate_utci_polygons(
                putci,
                merge_polygons=bool(spec.get("merge_polygons", True)),
                stress_polygons=spec.get("stress_polygons"),
            )
            utci_stats = dict(utci_eval["statistics"])
            utci_stats["relative_humidity_source"] = rh_source

            t_pairs = [
                putci.max_min_air_temperatures(idx, [ref_rh])[0]
                for idx in range(putci.polygon_count)
            ]
            t_low_c = min(p[0] for p in t_pairs)
            t_high_c = max(p[1] for p in t_pairs)
            band_res = _adaptive_band_segments(chart, t_low_c, t_high_c)
            if band_res is not None:
                band_poly, y_low, y_high = band_res
                vis_set.add_geometry(
                    ContextGeometry(
                        "UTCI_Comfort_Polygon",
                        _polygon_segments_to_display(
                            (band_poly,),
                            z_value=z_value,
                            color=Color(210, 120, 30),
                            line_width=2,
                        ),
                    )
                )
                utci_band_bounds = {
                    "operative_min": y_low,
                    "operative_max": y_high,
                    "reference_relative_humidity": ref_rh,
                }

        if poly_model == "pmv":
            polygon_summary = dict(pmv_stats or {})
            if pmv_band_bounds is not None:
                polygon_summary["operative_band"] = pmv_band_bounds
        elif poly_model == "utci":
            polygon_summary = dict(utci_stats or {})
            if utci_band_bounds is not None:
                polygon_summary["operative_band"] = utci_band_bounds
        else:
            polygon_summary = {
                "model": "both",
                "pmv": {**(pmv_stats or {}), **({"operative_band": pmv_band_bounds} if pmv_band_bounds else {})},
                "utci": {**(utci_stats or {}), **({"operative_band": utci_band_bounds} if utci_band_bounds else {})},
            }

    safe_name = slugify_name(name)
    vis_set.identifier = safe_name
    vis_set.display_name = name
    visualization_set = vis_set.to_dict()
    source = {
        "producer": "adaptive_chart_to_visualization_set",
        "outdoor_temperature_target": outdoor_temperature_target,
        "operative_temperature_target": operative_temperature_target,
        "air_temperature_target": air_temperature_target,
        "relative_humidity_target": relative_humidity_target,
        "strategy_layers": layer_summaries,
        "comfort_polygon": polygon_summary,
        "passive_strategy_statistics": passive_stats,
        "use_ip": bool(use_ip),
        "z": z_value,
    }
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
    )
    summary_view = {
        "garden_target": manifest.target(),
        "source": source,
        "visualization_set": _visualization_set_summary(visualization_set),
        "visualization_set_target": saved["visualization_set_target"],
        "comfort_percentages": percentages,
        "comfort_polygon": polygon_summary,
        "passive_strategy_statistics": passive_stats,
        "strategy_layers": layer_summaries,
        "body_returned": bool(return_visualization_set),
    }
    result: dict[str, Any] = {
        "target": saved["target"],
        "visualization_set_target": saved["visualization_set_target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="Adaptive chart VisualizationSet created.",
        ),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result


__all__ = [
    "adaptive_chart_to_visualization_set",
    "psychrometric_chart_to_visualization_set",
]
