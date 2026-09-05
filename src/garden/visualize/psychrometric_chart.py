"""Garden-backed Ladybug psychrometric chart visualization service."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Any

from ladybug.legend import LegendParameters
from ladybug.psychchart import PsychrometricChart
from ladybug_display.extension.psychchart import psychrometric_chart_to_vis_set
from ladybug_geometry.geometry2d import Point2D

from garden.data_collection import (
    DATA_COLLECTION_TARGET_TYPE,
    data_collection_summary,
    load_data_collection,
)
from garden.manifest import GardenManifest
from garden.paths import slugify_name
from garden.visualize.artifacts import save_visualization_set
from garden.visualize.legend import legend_parameter_from_dict
from ladybug_tools_mcp.contracts.report import make_report


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


def _legend_parameter(data: dict[str, Any] | None) -> LegendParameters | None:
    if data is None:
        return None
    try:
        return legend_parameter_from_dict(data)
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


def psychrometric_chart_to_visualization_set(
    *,
    garden_root: str,
    temperature_target: dict[str, Any],
    relative_humidity_target: dict[str, Any],
    strategy_layers: list[dict[str, Any]] | None = None,
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
    """Create and persist a psychrometric chart with optional strategy layers."""
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


__all__ = ["psychrometric_chart_to_visualization_set"]
