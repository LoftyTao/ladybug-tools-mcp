"""Garden-backed Ladybug psychrometric and adaptive chart visualization services."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Any

from ladybug.color import Color
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


def _resolve_polygon_numeric_or_seq(
    *,
    garden_root_path: Path,
    value: Any,
    field_name: str,
) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        col = _load_collection(garden_root=garden_root_path, target=value, field_name=field_name)
        return [float(v) for v in col.values]
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]
    raise ValueError(f"{field_name} must be a number, list of numbers, or DataCollection target.")


def _apply_comfort_polygon(
    *,
    vis_set: Any,
    chart: PsychrometricChart,
    garden_root_path: Path,
    comfort_polygon: dict[str, Any],
    z_value: float,
) -> dict[str, Any]:
    poly_model = str(comfort_polygon.get("model") or comfort_polygon.get("type") or "pmv").strip().lower()
    summary: dict[str, Any] = {"model": poly_model}
    rad_temp = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=comfort_polygon.get("rad_temperature") or comfort_polygon.get("mean_radiant_temperature_target"),
        field_name="comfort_polygon.rad_temperature",
    )

    if poly_model == "utci":
        wind_speed = _resolve_polygon_numeric_or_seq(
            garden_root_path=garden_root_path,
            value=comfort_polygon.get("wind_speed") or comfort_polygon.get("wind_speed_target"),
            field_name="comfort_polygon.wind_speed",
        )
        utci_par = None
        if comfort_polygon.get("comfort_parameter"):
            p_data = dict(comfort_polygon["comfort_parameter"])
            p_data.setdefault("type", "UTCIParameter")
            utci_par = UTCIParameter.from_dict(p_data)
        putci = PolygonUTCI(
            chart,
            rad_temperature=rad_temp,
            wind_speed=wind_speed,
            comfort_parameter=utci_par,
        )
        comfort_vals = list(putci.merged_comfort_values)
        comfort_pct = sum(comfort_vals) / len(comfort_vals) * 100.0 if comfort_vals else 0.0
        vis_set.add_geometry(
            ContextGeometry(
                "Comfort_Polygon",
                _polygon_segments_to_display(
                    putci.merged_comfort_polygon,
                    z_value=z_value,
                    color=Color(0, 150, 100),
                    line_width=3,
                ),
            )
        )
        stress_spec = comfort_polygon.get("stress_polygons")
        stress_names = (
            [
                "moderate_cold",
                "strong_cold",
                "very_strong_cold",
                "moderate_heat",
                "strong_heat",
                "very_strong_heat",
            ]
            if stress_spec is True
            else list(stress_spec or [])
        )
        stress_colors = {
            "moderate_cold": Color(100, 170, 230),
            "strong_cold": Color(40, 100, 210),
            "very_strong_cold": Color(15, 45, 160),
            "moderate_heat": Color(240, 170, 50),
            "strong_heat": Color(230, 95, 25),
            "very_strong_heat": Color(180, 20, 20),
        }
        added_stress: list[str] = []
        for s_name in stress_names:
            attr = f"{s_name}_polygon"
            if hasattr(putci, attr):
                segs = getattr(putci, attr)
                if segs:
                    vis_set.add_geometry(
                        ContextGeometry(
                            f"UTCI_{s_name}",
                            _polygon_segments_to_display(
                                segs,
                                z_value=z_value,
                                color=stress_colors.get(s_name, Color(120, 120, 120)),
                                line_width=2,
                            ),
                        )
                    )
                    added_stress.append(s_name)
        summary.update(
            {
                "polygon_count": putci.polygon_count,
                "comfort_percent": comfort_pct,
                "stress_polygons": added_stress,
            }
        )
        return summary

    if poly_model != "pmv":
        raise ValueError("comfort_polygon.model must be 'pmv' or 'utci'.")

    air_speed = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=comfort_polygon.get("air_speed") or comfort_polygon.get("air_speed_target"),
        field_name="comfort_polygon.air_speed",
    )
    met_rate = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=comfort_polygon.get("met_rate"),
        field_name="comfort_polygon.met_rate",
    )
    clo_value = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=comfort_polygon.get("clo_value"),
        field_name="comfort_polygon.clo_value",
    )
    external_work = _resolve_polygon_numeric_or_seq(
        garden_root_path=garden_root_path,
        value=comfort_polygon.get("external_work"),
        field_name="comfort_polygon.external_work",
    )
    pmv_par = None
    if comfort_polygon.get("comfort_parameter"):
        p_data = dict(comfort_polygon["comfort_parameter"])
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
    comfort_vals = list(ppmv.merged_comfort_values)
    comfort_pct = sum(comfort_vals) / len(comfort_vals) * 100.0 if comfort_vals else 0.0
    vis_set.add_geometry(
        ContextGeometry(
            "Comfort_Polygon",
            _polygon_segments_to_display(
                ppmv.merged_comfort_polygon,
                z_value=z_value,
                color=Color(0, 150, 100),
                line_width=3,
            ),
        )
    )

    strategy_percents: dict[str, float] = {}
    strategy_layers_added: list[str] = []
    strategies = comfort_polygon.get("strategies") or []
    if isinstance(strategies, dict):
        enabled = [k for k, v in strategies.items() if v]
    else:
        enabled = [str(s).strip().lower() for s in strategies]

    def _eval_pct(poly_segs: Any) -> float:
        vals = ppmv.evaluate_polygon(poly_segs)
        return sum(vals) / len(vals) * 100.0 if vals else 0.0

    if "evaporative_cooling" in enabled:
        segs = ppmv.evaporative_cooling_polygon()
        if segs:
            vis_set.add_geometry(
                ContextGeometry(
                    "Evaporative_Cooling_Polygon",
                    _polygon_segments_to_display(segs, z_value=z_value, color=Color(0, 130, 210)),
                )
            )
            strategy_layers_added.append("evaporative_cooling")
            strategy_percents["evaporative_cooling"] = _eval_pct(segs)

    if "fan_use" in enabled:
        fan_speed = float(comfort_polygon.get("fan_air_speed", 1.0))
        segs = ppmv.fan_use_polygon(air_speed=fan_speed)
        if segs:
            vis_set.add_geometry(
                ContextGeometry(
                    "Fan_Use_Polygon",
                    _polygon_segments_to_display(segs, z_value=z_value, color=Color(30, 180, 180)),
                )
            )
            strategy_layers_added.append("fan_use")
            strategy_percents["fan_use"] = _eval_pct(segs)

    if "night_flush" in enabled:
        tac = float(comfort_polygon.get("night_flush_temp_above_comfort", 12.0))
        segs = ppmv.night_flush_polygon(temperature_above_comfort=tac)
        if segs:
            vis_set.add_geometry(
                ContextGeometry(
                    "Night_Flush_Polygon",
                    _polygon_segments_to_display(segs, z_value=z_value, color=Color(80, 90, 200)),
                )
            )
            strategy_layers_added.append("night_flush")
            out_t_target = comfort_polygon.get("outdoor_temperature_target")
            if out_t_target is not None:
                out_t = _load_collection(
                    garden_root=garden_root_path,
                    target=out_t_target,
                    field_name="comfort_polygon.outdoor_temperature_target",
                )
                vals = ppmv.evaluate_night_flush_polygon(
                    segs,
                    out_t,
                    night_below_comfort=float(comfort_polygon.get("night_below_comfort", 3.0)),
                    time_constant=int(comfort_polygon.get("time_constant", 8)),
                )
                strategy_percents["night_flush"] = sum(vals) / len(vals) * 100.0 if vals else 0.0
            else:
                strategy_percents["night_flush"] = _eval_pct(segs)

    if "internal_heat" in enabled:
        bal_t = float(comfort_polygon.get("internal_heat_balance_temperature", 12.8))
        segs = ppmv.internal_heat_polygon(balance_temperature=bal_t)
        if segs:
            vis_set.add_geometry(
                ContextGeometry(
                    "Internal_Heat_Polygon",
                    _polygon_segments_to_display(segs, z_value=z_value, color=Color(210, 140, 40)),
                )
            )
            strategy_layers_added.append("internal_heat")
            strategy_percents["internal_heat"] = _eval_pct(segs)

    if "passive_solar" in enabled:
        bal_t_raw = comfort_polygon.get("passive_solar_balance_temperature")
        bal_t_val = float(bal_t_raw) if bal_t_raw is not None else None
        irr_target = comfort_polygon.get("incident_irradiance_target")
        if irr_target is not None:
            irr_col = _load_collection(
                garden_root=garden_root_path,
                target=irr_target,
                field_name="comfort_polygon.incident_irradiance_target",
            )
            vals, max_delta = ppmv.evaluate_passive_solar(
                irr_col,
                solar_heat_capacity=float(comfort_polygon.get("solar_heat_capacity", 50.0)),
                time_constant=int(comfort_polygon.get("time_constant", 8)),
                balance_temperature=bal_t_val,
            )
            strategy_percents["passive_solar"] = sum(vals) / len(vals) * 100.0 if vals else 0.0
        else:
            max_delta = float(comfort_polygon.get("passive_solar_max_delta", 10.0))
        segs = ppmv.passive_solar_polygon(max_delta, balance_temperature=bal_t_val)
        if segs:
            vis_set.add_geometry(
                ContextGeometry(
                    "Passive_Solar_Polygon",
                    _polygon_segments_to_display(segs, z_value=z_value, color=Color(225, 195, 30)),
                )
            )
            strategy_layers_added.append("passive_solar")
            if "passive_solar" not in strategy_percents:
                strategy_percents["passive_solar"] = _eval_pct(segs)

    if "shade_line" in enabled:
        shade_bal = float(comfort_polygon.get("shade_balance_temperature", 12.8))
        shade_segs = ppmv.shade_line(balance_temperature=shade_bal)
        if not shade_segs:
            bp_x = chart.t_x_value(shade_bal if not chart.use_ip else shade_bal * 1.8 + 32.0)
            comf_poly = ppmv.merged_comfort_polygon
            shade_segs = (
                LineSegment2D.from_end_points(
                    Point2D(bp_x, chart.base_point.y),
                    Point2D(bp_x, comf_poly[0][0].y),
                ),
            )
        elif not isinstance(shade_segs, (list, tuple)):
            shade_segs = (shade_segs,)
        vis_set.add_geometry(
            ContextGeometry(
                "Shade_Line",
                _polygon_segments_to_display(shade_segs, z_value=z_value, color=Color(110, 110, 110)),
            )
        )
        strategy_layers_added.append("shade_line")

    summary.update(
        {
            "polygon_count": ppmv.polygon_count,
            "comfort_percent": comfort_pct,
            "strategies_added": strategy_layers_added,
            "strategy_percents": strategy_percents,
        }
    )
    return summary


def psychrometric_chart_to_visualization_set(
    *,
    garden_root: str,
    temperature_target: dict[str, Any],
    relative_humidity_target: dict[str, Any],
    strategy_layers: list[dict[str, Any]] | None = None,
    comfort_polygon: dict[str, Any] | None = None,
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

    polygon_summary = None
    if comfort_polygon is not None:
        polygon_summary = _apply_comfort_polygon(
            vis_set=vis_set,
            chart=chart,
            garden_root_path=garden_root_path,
            comfort_polygon=comfort_polygon,
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


def adaptive_chart_to_visualization_set(
    *,
    garden_root: str,
    outdoor_temperature_target: dict[str, Any],
    operative_temperature_target: dict[str, Any] | None = None,
    air_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
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
    air_speed = (
        _load_collection(
            garden_root=garden_root_path,
            target=air_speed_target,
            field_name="air_speed_target",
        )
        if air_speed_target is not None
        else None
    )
    adp_par = None
    if comfort_parameter is not None:
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
            air_speed=air_speed,
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
            air_speed=air_speed,
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
    vis_set = adaptive_chart_to_vis_set(
        vis_chart,
        data=collections or None,
        legend_parameters=legends or None,
        z=float(z),
    )
    safe_name = slugify_name(name)
    vis_set.identifier = safe_name
    vis_set.display_name = name
    visualization_set = vis_set.to_dict()
    source = {
        "producer": "adaptive_chart_to_visualization_set",
        "outdoor_temperature_target": outdoor_temperature_target,
        "operative_temperature_target": operative_temperature_target,
        "air_temperature_target": air_temperature_target,
        "strategy_layers": layer_summaries,
        "use_ip": bool(use_ip),
        "z": float(z),
    }
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
    )
    percentages = {
        "comfortable": chart.percent_comfortable,
        "uncomfortable": chart.percent_uncomfortable,
        "neutral": chart.percent_neutral,
        "cold": chart.percent_cold,
        "hot": chart.percent_hot,
    }
    summary_view = {
        "garden_target": manifest.target(),
        "source": source,
        "visualization_set": _visualization_set_summary(visualization_set),
        "visualization_set_target": saved["visualization_set_target"],
        "comfort_percentages": percentages,
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
