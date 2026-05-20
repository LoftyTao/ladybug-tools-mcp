"""Weather file DataCollection services."""

from __future__ import annotations

import re
from pathlib import Path
from statistics import mean
from typing import Any

from ladybug.epw import EPW

from ladybug_tools_mcp.contracts.report import make_report
from garden.analysis_period import analysis_period_from_input, analysis_period_summary
from garden.data_collection import save_data_collection
from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.run_energy.config import WEATHER_TARGET_TYPE

_EPW_DATA_FIELDS = {
    "aerosol_optical_depth",
    "albedo",
    "atmospheric_station_pressure",
    "ceiling_height",
    "days_since_last_snowfall",
    "dew_point_temperature",
    "diffuse_horizontal_illuminance",
    "diffuse_horizontal_radiation",
    "direct_normal_illuminance",
    "direct_normal_radiation",
    "dry_bulb_temperature",
    "extraterrestrial_direct_normal_radiation",
    "extraterrestrial_horizontal_radiation",
    "global_horizontal_illuminance",
    "global_horizontal_radiation",
    "horizontal_infrared_radiation_intensity",
    "liquid_precipitation_depth",
    "liquid_precipitation_quantity",
    "opaque_sky_cover",
    "precipitable_water",
    "relative_humidity",
    "sky_temperature",
    "snow_depth",
    "total_sky_cover",
    "visibility",
    "wind_direction",
    "wind_speed",
    "zenith_luminance",
}

def _normalize_data_type(value: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if key not in _EPW_DATA_FIELDS:
        allowed = ", ".join(sorted(_EPW_DATA_FIELDS))
        raise ValueError(
            f"Unsupported EPW data_type: {value}. Allowed: {allowed}."
        )
    return key


def _resolve_garden_epw_path(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Path, dict[str, Any]]:
    has_target = weather_target is not None
    has_path = epw_path is not None
    if has_target == has_path:
        raise ValueError("Provide exactly one of weather_target or epw_path.")

    if has_target:
        if not isinstance(weather_target, dict):
            raise ValueError("weather_target must be a dictionary.")
        target_type = weather_target.get("target_type")
        if target_type != WEATHER_TARGET_TYPE:
            raise ValueError(
                "weather_target target_type must be "
                f"{WEATHER_TARGET_TYPE!r}; got {target_type!r}."
            )
        target_garden_id = weather_target.get("garden_id")
        if target_garden_id != manifest.garden_id:
            raise ValueError("weather_target garden_id does not match the Garden root.")
        raw_path = weather_target.get("epw_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("weather_target requires epw_path.")
        source = {
            "source_type": "weather_target",
            "identifier": weather_target.get("identifier"),
            "station": weather_target.get("station"),
            "epw_path": raw_path,
        }
    else:
        raw_path = str(epw_path or "").strip()
        if not raw_path:
            raise ValueError("epw_path cannot be empty.")
        source = {
            "source_type": "epw_path",
            "identifier": Path(raw_path).stem,
            "epw_path": raw_path.replace("\\", "/"),
        }

    path = Path(raw_path).expanduser()
    resolved = (
        path.resolve()
        if path.is_absolute()
        else (garden_root_path / path).resolve()
    )
    try:
        resolved.relative_to(garden_root_path)
    except ValueError as exc:
        raise ValueError("Weather file path must resolve inside the Garden.") from exc
    if resolved.suffix.lower() != ".epw":
        raise ValueError(f"Weather file must be an .epw file: {raw_path}")
    if not resolved.is_file():
        raise ValueError(f"Weather file was not found: {raw_path}")
    source["epw_path"] = to_posix_relative(resolved, garden_root_path)
    return resolved, source


def _collection_name(collection: Any, default_name: str) -> str:
    if hasattr(collection, "ToString"):
        try:
            value = str(collection.ToString()).strip()
            if value:
                return value
        except Exception:
            pass
    return default_name


def _header_value(header: Any, attr: str) -> Any:
    value = getattr(header, attr, None)
    if attr == "data_type" and value is not None:
        return getattr(value, "name", str(value))
    return value


def _collection_summary(
    collection: Any,
    *,
    data_type: str,
    weather_file: dict[str, Any],
    include_values: bool,
    max_values: int,
    analysis_period_input: dict[str, Any] | str | None,
) -> dict[str, Any]:
    values = list(getattr(collection, "values", []) or [])
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    header = getattr(collection, "header", None)
    analysis_period = (
        getattr(header, "analysis_period", None) if header is not None else None
    )
    summary: dict[str, Any] = {
        "name": _collection_name(collection, data_type),
        "collection_type": type(collection).__name__,
        "data_type": _header_value(header, "data_type") if header is not None else None,
        "epw_data_type": data_type,
        "unit": _header_value(header, "unit") if header is not None else None,
        "metadata": (
            dict(getattr(header, "metadata", {}) or {}) if header is not None else {}
        ),
        "value_count": len(values),
        "minimum": min(numeric_values) if numeric_values else None,
        "maximum": max(numeric_values) if numeric_values else None,
        "mean": mean(numeric_values) if numeric_values else None,
        "weather_file": weather_file,
        "analysis_period_input": analysis_period_input,
    }
    if analysis_period is not None:
        summary["analysis_period"] = analysis_period_summary(analysis_period)
    if include_values:
        visible_values = values[:max_values]
        summary["values"] = visible_values
        summary["values_truncated"] = len(values) > len(visible_values)
    return summary


def read_weather_file_data(
    *,
    garden_root: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    data_type: str = "dry_bulb_temperature",
    analysis_period: dict[str, Any] | str | None = None,
    identifier: str | None = None,
    include_values: bool = False,
    max_values: int = 24,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Read a Garden EPW weather file field as a Ladybug DataCollection target."""
    if max_values < 0:
        raise ValueError("max_values must be zero or greater.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    epw_data_type = _normalize_data_type(data_type)
    resolved_epw_path, weather_file = _resolve_garden_epw_path(
        garden_root_path=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
    )

    epw = EPW(str(resolved_epw_path))
    collection = getattr(epw, epw_data_type)
    if hasattr(collection, "duplicate"):
        collection = collection.duplicate()

    parsed_analysis_period = analysis_period_from_input(
        analysis_period,
        field_name="analysis_period",
    )
    if parsed_analysis_period is not None and not parsed_analysis_period.is_annual:
        collection = collection.filter_by_analysis_period(parsed_analysis_period)

    header = getattr(collection, "header", None)
    if header is not None:
        header.metadata["source"] = "epw_weather_file"
        header.metadata["epw_data_type"] = epw_data_type
        header.metadata["epw_path"] = weather_file["epw_path"]
        if weather_file.get("identifier"):
            header.metadata["weather_identifier"] = weather_file["identifier"]

    safe_identifier = (
        identifier
        or f"{weather_file.get('identifier') or resolved_epw_path.stem}_{epw_data_type}"
    )
    source = {
        "producer": "read_weather_file_data",
        "weather_file": weather_file,
        "epw_data_type": epw_data_type,
        "analysis_period": (
            analysis_period_summary(parsed_analysis_period)
            if parsed_analysis_period is not None
            else None
        ),
    }
    saved = save_data_collection(
        garden_root=garden_root_path,
        data_collection=collection,
        identifier=safe_identifier,
        source=source,
    )
    summary_view = _collection_summary(
        collection,
        data_type=epw_data_type,
        weather_file=weather_file,
        include_values=include_values,
        max_values=max_values,
        analysis_period_input=analysis_period,
    )
    summary_view["data_collection_target"] = saved["target"]

    result = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="Weather file DataCollection persisted.",
        ),
    }
    if return_data_collection:
        result["data_collection"] = collection.to_dict()
    return result
