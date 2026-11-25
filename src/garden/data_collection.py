"""Garden-backed Ladybug DataCollection storage, analytics, and summaries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean, pstdev, stdev
from typing import Any

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datacollection import (
    BaseCollection,
    DailyCollection,
    HourlyContinuousCollection,
    HourlyDiscontinuousCollection,
    MonthlyCollection,
    MonthlyPerHourCollection,
)
from ladybug.datatype import TYPESDICT
from ladybug.datatype.base import DataTypeBase
from ladybug.datatype.generic import GenericType
from ladybug.datatype.temperaturetime import CoolingDegreeTime, HeatingDegreeTime
from ladybug.datautil import (
    collections_from_csv,
    collections_from_json,
    collections_from_pkl,
    collections_to_csv,
    collections_to_json,
    collections_to_pkl,
)
from ladybug.dt import Date, DateTime
from ladybug.header import Header
from ladybug_comfort.degreetime import cooling_degree_time, heating_degree_time

from garden.analysis_period import analysis_period_from_input
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

DATA_COLLECTION_TARGET_TYPE = "ladybug_data_collection"
DATA_COLLECTION_ARTIFACT_TYPE = "data_collection_json"
DATA_COLLECTION_CSV_ARTIFACT_TYPE = "data_collection_csv"
DATA_COLLECTION_PKL_ARTIFACT_TYPE = "data_collection_pkl"
DATA_COLLECTION_OUTPUT_SUBDIR = "artifacts/data_collections"
_DATA_COLLECTION_ARTIFACT_TYPES = {
    "json": DATA_COLLECTION_ARTIFACT_TYPE,
    "csv": DATA_COLLECTION_CSV_ARTIFACT_TYPE,
    "pkl": DATA_COLLECTION_PKL_ARTIFACT_TYPE,
}

_COLLECTION_CLASSES = {
    "HourlyContinuous": HourlyContinuousCollection,
    "HourlyDiscontinuous": HourlyDiscontinuousCollection,
    "Daily": DailyCollection,
    "Monthly": MonthlyCollection,
    "MonthlyPerHour": MonthlyPerHourCollection,
}

_COLLECTION_ALIASES = {
    "hourly": HourlyContinuousCollection,
    "hourly_continuous": HourlyContinuousCollection,
    "hourlycontinuous": HourlyContinuousCollection,
    "hourly_discontinuous": HourlyDiscontinuousCollection,
    "hourlydiscontinuous": HourlyDiscontinuousCollection,
    "daily": DailyCollection,
    "monthly": MonthlyCollection,
    "monthly_per_hour": MonthlyPerHourCollection,
    "monthlyperhour": MonthlyPerHourCollection,
}


def data_collection_summary(data_collection: Any) -> dict[str, Any]:
    """Return a compact summary for a Ladybug DataCollection."""
    header = data_collection.header
    values = data_collection.values
    analysis_period = header.analysis_period.to_dict()
    return {
        "type": data_collection.to_dict().get("type"),
        "unit": header.unit,
        "data_type": header.data_type.to_dict(),
        "analysis_period": analysis_period,
        "metadata": dict(header.metadata),
        "timestep": analysis_period.get("timestep"),
        "value_count": len(values),
        "min": data_collection.min,
        "max": data_collection.max,
        "average": data_collection.average,
        "median": data_collection.median,
        "total": data_collection.total,
        "is_continuous": data_collection.is_continuous,
    }


def collection_from_dict(data: dict[str, Any]) -> Any:
    """Rebuild a Ladybug DataCollection from an SDK dictionary."""
    collection_type = str(data.get("type") or "")
    collection_cls = _COLLECTION_CLASSES.get(collection_type)
    if collection_cls is None:
        allowed = ", ".join(sorted(_COLLECTION_CLASSES))
        raise ValueError(
            f"Unsupported DataCollection type: {collection_type}. Allowed: {allowed}."
        )
    return collection_cls.from_dict(data)


def _target(*, manifest: GardenManifest, identifier: str, path: str) -> dict[str, Any]:
    return {
        "target_type": DATA_COLLECTION_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": "ladybug",
        "identifier": identifier,
        "path": path,
    }


def _register_artifact(
    manifest: GardenManifest,
    *,
    name: str,
    path: str,
    source: dict[str, Any],
    artifact_type: str = DATA_COLLECTION_ARTIFACT_TYPE,
) -> dict[str, Any]:
    return manifest.upsert_artifact(
        {
            "artifact_type": artifact_type,
            "name": name,
            "path": path,
            "source": source,
            "created_at": utc_now_iso(),
        }
    )


def _coerce_collection(data_collection: Any | dict[str, Any]) -> Any:
    collection = (
        collection_from_dict(data_collection)
        if isinstance(data_collection, dict)
        else data_collection
    )
    if not hasattr(collection, "to_dict"):
        raise ValueError("data_collection must be a Ladybug DataCollection object or dict.")
    return collection


def _write_collection_file(
    *,
    collections: list[Any],
    output_dir: Path,
    file_name: str,
    file_format: str,
) -> Path:
    file_format = file_format.lower()
    if file_format == "json":
        return Path(collections_to_json(collections, str(output_dir), file_name))
    if file_format == "csv":
        return Path(collections_to_csv(collections, str(output_dir), file_name))
    if file_format == "pkl":
        return Path(collections_to_pkl(collections, str(output_dir), file_name))
    raise ValueError("file_format must be one of: json, csv, pkl.")


def _load_json_collections(data_path: Path) -> list[Any]:
    with data_path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)
    if isinstance(raw_data, dict):
        return [collection_from_dict(raw_data)]
    return list(collections_from_json(str(data_path)))


def _load_json_collection(data_path: Path) -> Any:
    collections = _load_json_collections(data_path)
    if len(collections) != 1:
        raise ValueError(
            f"DataCollection JSON target must contain one collection; got {len(collections)}."
        )
    return collections[0]


def _load_csv_collection(data_path: Path) -> Any:
    collections = list(collections_from_csv(str(data_path)))
    if len(collections) != 1:
        raise ValueError(
            f"DataCollection CSV target must contain one collection; got {len(collections)}."
        )
    return collections[0]


def _load_pkl_collection(data_path: Path) -> Any:
    collections = list(collections_from_pkl(str(data_path)))
    if len(collections) != 1:
        raise ValueError(
            f"DataCollection PKL target must contain one collection; got {len(collections)}."
        )
    return collections[0]


def save_data_collection(
    *,
    garden_root: str | Path,
    data_collection: Any | dict[str, Any],
    identifier: str,
    output_subdir: str = DATA_COLLECTION_OUTPUT_SUBDIR,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a Ladybug DataCollection and return a compact Garden target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    collection = _coerce_collection(data_collection)

    safe_identifier = slugify_name(identifier)
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = (output_dir / f"{safe_identifier}.json").resolve()
    data_path.relative_to(garden_root_path)
    data_dict = collection.to_dict()
    _write_collection_file(
        collections=[collection],
        output_dir=output_dir,
        file_name=data_path.name,
        file_format="json",
    )

    artifact_path = to_posix_relative(data_path, garden_root_path)
    artifact_source = {"data_collection_type": data_dict.get("type"), **(source or {})}
    artifact = _register_artifact(
        manifest, name=safe_identifier, path=artifact_path, source=artifact_source
    )
    manifest.write(garden_root_path)
    target = _target(manifest=manifest, identifier=safe_identifier, path=artifact_path)
    return {
        "target": target,
        "data_target": target,
        "summary_view": data_collection_summary(collection),
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=DATA_COLLECTION_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(data_path),
            source=artifact_source,
        ),
    }


def export_data_collection_file(
    *,
    garden_root: str | Path,
    data_collection: Any | dict[str, Any] | None = None,
    data_collection_target: dict[str, Any] | None = None,
    data_collections: list[Any | dict[str, Any]] | None = None,
    data_collection_targets: list[dict[str, Any]] | None = None,
    file_format: str = "json",
    name: str = "data_collection",
    output_subdir: str = DATA_COLLECTION_OUTPUT_SUBDIR,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export one or more Ladybug DataCollections to a native SDK JSON, CSV, or PKL artifact."""
    normalized_format = file_format.lower().strip()
    artifact_type = _DATA_COLLECTION_ARTIFACT_TYPES.get(normalized_format)
    if artifact_type is None:
        raise ValueError("file_format must be one of: json, csv, pkl.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)

    collections: list[Any] = []
    if data_collection is not None:
        collections.append(_coerce_collection(data_collection))
    if data_collection_target is not None:
        collections.append(
            load_data_collection(
                garden_root=garden_root_path,
                data_collection_target=data_collection_target,
            )
        )
    for item in data_collections or []:
        collections.append(_coerce_collection(item))
    for tgt in data_collection_targets or []:
        collections.append(
            load_data_collection(
                garden_root=garden_root_path,
                data_collection_target=tgt,
            )
        )
    if not collections:
        raise ValueError(
            "export_data_collection_file requires at least one DataCollection dict or target."
        )

    safe_name = slugify_name(name)
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = (output_dir / f"{safe_name}.{normalized_format}").resolve()
    data_path.relative_to(garden_root_path)
    written_path = _write_collection_file(
        collections=collections,
        output_dir=output_dir,
        file_name=data_path.name,
        file_format=normalized_format,
    ).resolve()
    written_path.relative_to(garden_root_path)

    collection_types = [item.to_dict().get("type") for item in collections]
    artifact_path = to_posix_relative(written_path, garden_root_path)
    artifact_source = {
        "data_collection_type": collection_types[0] if len(collection_types) == 1 else collection_types,
        "collection_count": len(collections),
        "file_format": normalized_format,
        **(source or {}),
    }
    artifact = _register_artifact(
        manifest,
        name=safe_name,
        path=artifact_path,
        source=artifact_source,
        artifact_type=artifact_type,
    )
    manifest.write(garden_root_path)
    target = _target(manifest=manifest, identifier=safe_name, path=artifact_path)
    summary_view: dict[str, Any] = (
        data_collection_summary(collections[0])
        if len(collections) == 1
        else {
            "collection_count": len(collections),
            "collections": [data_collection_summary(item) for item in collections],
            "file_format": normalized_format,
        }
    )
    return {
        "target": target,
        "data_collection_target": target,
        "summary_view": summary_view,
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            absolute_path=str(written_path),
            source=artifact_source,
        ),
    }


def load_data_collection(
    *,
    garden_root: str | Path,
    data_collection_target: dict[str, Any],
) -> Any:
    """Load a Garden-backed Ladybug DataCollection target."""
    if not isinstance(data_collection_target, dict):
        raise ValueError("data_collection_target must be a dictionary.")
    target_type = data_collection_target.get("target_type")
    if target_type != DATA_COLLECTION_TARGET_TYPE:
        raise ValueError(
            "data_collection_target target_type must be "
            f"{DATA_COLLECTION_TARGET_TYPE!r}; got {target_type!r}."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    if data_collection_target.get("garden_id") != manifest.garden_id:
        raise ValueError(
            "data_collection_target garden_id does not match the Garden root."
        )
    target_path = data_collection_target.get("path")
    if not isinstance(target_path, str) or not target_path:
        raise ValueError("data_collection_target requires a Garden-relative path.")
    data_path = (garden_root_path / target_path).resolve()
    data_path.relative_to(garden_root_path)
    if not data_path.is_file():
        raise ValueError(f"DataCollection target file was not found: {target_path}")
    suffix = data_path.suffix.lower()
    if suffix == ".json":
        return _load_json_collection(data_path)
    if suffix == ".csv":
        return _load_csv_collection(data_path)
    if suffix == ".pkl":
        return _load_pkl_collection(data_path)
    raise ValueError(
        f"DataCollection target must point to a .json, .csv, or .pkl file: {target_path}"
    )


def _resolve_single_collection(
    *,
    garden_root_path: Path,
    data_collection: dict[str, Any] | None,
    data_collection_target: dict[str, Any] | None,
    field_name: str = "data_collection",
) -> Any:
    if (data_collection is None) == (data_collection_target is None):
        raise ValueError(
            f"{field_name} requires exactly one of data_collection or data_collection_target."
        )
    if data_collection is not None:
        return _coerce_collection(data_collection)
    return load_data_collection(
        garden_root=garden_root_path,
        data_collection_target=data_collection_target or {},
    )


def _resolve_datatype(data_type: dict[str, Any] | str | None) -> Any:
    if data_type is None:
        return GenericType("Generic", "unit")
    if isinstance(data_type, dict):
        return DataTypeBase.from_dict(data_type)
    text = str(data_type).strip()
    if not text:
        return GenericType("Generic", "unit")
    if text in TYPESDICT:
        return TYPESDICT[text]()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", text).lower()
    for key, cls in TYPESDICT.items():
        if key.lower() == normalized or cls.name.replace(" ", "").lower() == normalized:
            return cls()
    return GenericType(text, "unit")


def _parse_datetime_item(item: dict[str, Any] | str | int) -> Any:
    if isinstance(item, dict):
        if item.get("type") == "Date":
            return Date.from_dict(item)
        if "hour" in item:
            return DateTime.from_dict({"type": "DateTime", **item})
        return Date.from_dict({"type": "Date", **item})
    if isinstance(item, str):
        try:
            return DateTime.from_date_time_string(item)
        except Exception:
            return Date.from_date_string(item)
    raise ValueError(f"Unsupported datetime entry: {item!r}")


def _resolve_import_path(garden_root_path: Path, source_path: str) -> Path:
    raw = Path(source_path).expanduser()
    candidate = raw.resolve() if raw.is_absolute() else (garden_root_path / raw).resolve()
    if not candidate.is_file():
        raise ValueError(f"Import file not found: {source_path}")
    return candidate


def _inspect_collection(
    collection: Any,
    *,
    percentiles: list[float] | None,
    histogram_bins: int | list[float],
    include_values: bool,
    max_values: int,
) -> dict[str, Any]:
    values = list(collection.values)
    numeric = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    pct_points = percentiles if percentiles is not None else [5, 25, 50, 75, 95]
    percentile_map: dict[str, float] = {}
    for pct in pct_points:
        try:
            percentile_map[f"p{pct:g}"] = float(collection.percentile(pct))
        except Exception:
            pass
    try:
        if not numeric:
            hist_summary = []
        elif isinstance(histogram_bins, int):
            n_bins = max(1, int(histogram_bins))
            lo = float(min(numeric))
            hi = float(max(numeric))
            span = (hi - lo) if hi > lo else 1.0
            edges = [lo + i * span / n_bins for i in range(n_bins + 1)]
            raw_hist = list(collection.histogram(numeric, edges))
            mid = [list(raw_hist[i + 1]) for i in range(n_bins)]
            if raw_hist[0]:
                mid[0] = list(raw_hist[0]) + mid[0]
            if len(raw_hist) > n_bins + 1 and raw_hist[-1]:
                mid[-1] = mid[-1] + list(raw_hist[-1])
            hist_summary = [
                {"bin": [edges[i], edges[i + 1]], "count": len(mid[i])}
                for i in range(n_bins)
            ]
        else:
            edges = sorted(float(v) for v in histogram_bins)
            raw_hist = list(collection.histogram(numeric, edges))
            hist_summary = [
                {
                    "bin": [edges[i], edges[i + 1]] if i + 1 < len(edges) else [edges[-1], None],
                    "count": len(raw_hist[i + 1]) if i + 1 < len(raw_hist) else 0,
                }
                for i in range(max(0, len(edges) - 1))
            ]
    except Exception:
        hist_summary = []

    sample_std = stdev(numeric) if len(numeric) >= 2 else (0.0 if numeric else None)
    pop_std = pstdev(numeric) if len(numeric) >= 1 else None
    bounds = collection.bounds if numeric else (None, None)
    summary: dict[str, Any] = {
        **data_collection_summary(collection),
        "bounds": [bounds[0], bounds[1]],
        "mean": mean(numeric) if numeric else None,
        "std": sample_std,
        "population_std": pop_std,
        "percentiles": percentile_map,
        "histogram": hist_summary,
    }
    if include_values:
        visible = values[:max_values]
        summary["values"] = visible
        summary["values_truncated"] = len(values) > len(visible)
    return summary


def _persist_collection_result(
    *,
    garden_root_path: Path,
    collection: Any,
    identifier: str,
    source: dict[str, Any],
    message: str,
    return_data_collection: bool,
    extra_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    saved = save_data_collection(
        garden_root=garden_root_path,
        data_collection=collection,
        identifier=identifier,
        source=source,
    )
    summary_view = dict(saved["summary_view"])
    if extra_summary:
        summary_view.update(extra_summary)
    result: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(status="ok", message=message),
    }
    if return_data_collection:
        result["data_collection"] = collection.to_dict()
    return result


def _calculate_degree_days(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    col: Any,
    source_action: str,
    op_alias: str,
    degree_day_type: str,
    base_temperature: float | None,
    heating_base_temperature: float,
    cooling_base_temperature: float,
    identifier: str | None,
) -> dict[str, Any]:
    """Compute heating/cooling degree-hours and degree-days and persist DataCollections."""
    mode = (
        "heating"
        if op_alias == "heating_degree_days"
        else "cooling"
        if op_alias == "cooling_degree_days"
        else str(degree_day_type).strip().lower()
    )
    if mode not in {"heating", "cooling", "both"}:
        raise ValueError("degree_day_type must be one of: heating, cooling, both.")
    h_base = float(base_temperature) if base_temperature is not None else float(heating_base_temperature)
    c_base = float(base_temperature) if base_temperature is not None else float(cooling_base_temperature)
    ts = max(1, int(getattr(col.header.analysis_period, "timestep", 1) or 1))
    outputs: dict[str, Any] = {}
    summary_dd: dict[str, Any] = {}
    for kind, fn, dt_cls, b_temp in [
        ("heating", heating_degree_time, HeatingDegreeTime, h_base),
        ("cooling", cooling_degree_time, CoolingDegreeTime, c_base),
    ]:
        if mode not in {kind, "both"}:
            continue
        deg_vals = [float(fn(float(v), b_temp)) for v in col.values]
        dd_unit = "degF-hours" if str(col.header.unit) == "F" else "degC-hours"
        meta = dict(col.header.metadata or {})
        meta["base_temperature"] = b_temp
        hdr = Header(
            dt_cls(),
            dd_unit,
            col.header.analysis_period,
            metadata=meta,
        )
        if isinstance(col, HourlyContinuousCollection):
            dd_col = HourlyContinuousCollection(hdr, deg_vals)
        else:
            dd_col = type(col)(hdr, deg_vals, col.datetimes)
        saved_dd = save_data_collection(
            garden_root=garden_root_path,
            data_collection=dd_col,
            identifier=f"{identifier or 'degree_days'}_{kind}",
            source={
                "producer": "LB_Analyze_Data_Collection",
                "action": source_action,
                "operation": "degree_days",
                "kind": kind,
                "base_temperature": b_temp,
            },
        )
        outputs[kind] = saved_dd
        summary_dd[kind] = {
            "base_temperature": b_temp,
            "degree_hours_total": float(sum(deg_vals)),
            "degree_days_total": float(sum(deg_vals) / (24.0 * ts)),
            "target": saved_dd["target"],
        }
    primary_key = "heating" if "heating" in outputs else "cooling"
    primary = outputs[primary_key]
    return {
        "target": primary["target"],
        "data_target": primary["target"],
        "data_collection_target": primary["target"],
        "targets": {k: v["target"] for k, v in outputs.items()},
        "data_collection_targets": {k: v["target"] for k, v in outputs.items()},
        "artifact": primary["artifact"],
        "persistence_receipt": primary["persistence_receipt"],
        "summary_view": {
            "garden_target": manifest.target(),
            "operation": "degree_days",
            "degree_days": summary_dd,
        },
        "report": make_report(status="ok", message="Degree-days computed and persisted."),
    }


def analyze_data_collection(
    *,
    garden_root: str,
    action: str,
    data_collection: dict[str, Any] | None = None,
    data_collection_target: dict[str, Any] | None = None,
    data_collections: list[dict[str, Any]] | None = None,
    data_collection_targets: list[dict[str, Any]] | None = None,
    source_path: str | None = None,
    # create parameters
    values: list[float | int | str] | None = None,
    collection_type: str = "HourlyContinuous",
    header: dict[str, Any] | None = None,
    data_type: dict[str, Any] | str | None = None,
    unit: str | None = None,
    analysis_period: dict[str, Any] | str | None = None,
    metadata: dict[str, Any] | None = None,
    datetimes: list[dict[str, Any] | str] | None = None,
    # inspect parameters
    percentiles: list[float] | None = None,
    histogram_bins: int | list[float] = 10,
    include_values: bool = False,
    max_values: int = 24,
    # filter parameters
    filter_type: str | None = None,
    hoys: list[float] | None = None,
    greater_than: float | None = None,
    less_than: float | None = None,
    conditional_statement: str | None = None,
    pattern: list[bool] | None = None,
    # aggregate / math parameters
    operation: str | None = None,
    aggregation_method: str = "average",
    percentile_value: float = 50.0,
    timestep: int = 1,
    cumulative: bool | None = None,
    area: float | None = None,
    area_unit: str = "m2",
    target_unit: str | None = None,
    scalar: float | None = None,
    other_data_collection: dict[str, Any] | None = None,
    other_data_collection_target: dict[str, Any] | None = None,
    base_temperature: float | None = None,
    heating_base_temperature: float = 18.0,
    cooling_base_temperature: float = 23.0,
    degree_day_type: str = "both",
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Import, create, inspect, filter, aggregate, or perform math on Ladybug DataCollections."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    act = str(action).strip().lower()

    if act == "import":
        if not source_path:
            raise ValueError("source_path is required for action='import'.")
        import_file = _resolve_import_path(garden_root_path, source_path)
        suffix = import_file.suffix.lower()
        if suffix == ".csv":
            loaded = list(collections_from_csv(str(import_file)))
        elif suffix == ".json":
            loaded = _load_json_collections(import_file)
        elif suffix == ".pkl":
            loaded = list(collections_from_pkl(str(import_file)))
        else:
            raise ValueError("source_path must be a .csv, .json, or .pkl file.")
        if not loaded:
            raise ValueError(f"No DataCollections found in {source_path}.")
        base_id = slugify_name(identifier or import_file.stem)
        saved_items = [
            save_data_collection(
                garden_root=garden_root_path,
                data_collection=col,
                identifier=base_id if len(loaded) == 1 else f"{base_id}_{idx}",
                source={"producer": "LB_Analyze_Data_Collection", "action": "import", "source_path": str(import_file)},
            )
            for idx, col in enumerate(loaded, start=1)
        ]
        if len(saved_items) == 1:
            only = saved_items[0]
            res: dict[str, Any] = {
                "target": only["target"],
                "data_target": only["target"],
                "data_collection_target": only["target"],
                "targets": [only["target"]],
                "data_collection_targets": [only["target"]],
                "artifact": only["artifact"],
                "persistence_receipt": only["persistence_receipt"],
                "summary_view": {**only["summary_view"], "collection_count": 1},
                "report": make_report(status="ok", message="Imported 1 DataCollection."),
            }
            if return_data_collection:
                res["data_collection"] = loaded[0].to_dict()
            return res
        return {
            "target": saved_items[0]["target"],
            "targets": [s["target"] for s in saved_items],
            "data_collection_targets": [s["target"] for s in saved_items],
            "artifacts": [s["artifact"] for s in saved_items],
            "persistence_receipts": [s["persistence_receipt"] for s in saved_items],
            "summary_view": {
                "garden_target": manifest.target(),
                "collection_count": len(saved_items),
                "collections": [s["summary_view"] for s in saved_items],
            },
            "report": make_report(status="ok", message=f"Imported {len(saved_items)} DataCollections."),
        }

    if act == "create":
        if values is None:
            raise ValueError("values is required for action='create'.")
        if header is not None:
            hdr_dict = dict(header)
            if "analysis_period" not in hdr_dict or hdr_dict["analysis_period"] is None:
                hdr_dict["analysis_period"] = AnalysisPeriod().to_dict()
            if isinstance(hdr_dict.get("data_type"), str):
                hdr_dict["data_type"] = _resolve_datatype(hdr_dict["data_type"]).to_dict()
            hdr = Header.from_dict(hdr_dict)
        else:
            dt_obj = _resolve_datatype(data_type)
            ap_obj = analysis_period_from_input(analysis_period) or AnalysisPeriod()
            resolved_unit = unit if unit is not None else dt_obj.units[0]
            hdr = Header(dt_obj, resolved_unit, ap_obj, metadata=metadata)
        cls_key = re.sub(r"[^a-zA-Z0-9_]+", "", str(collection_type)).lower()
        col_cls = _COLLECTION_ALIASES.get(cls_key) or _COLLECTION_CLASSES.get(collection_type)
        if col_cls is None:
            allowed = ", ".join(sorted(_COLLECTION_CLASSES))
            raise ValueError(f"Unsupported collection_type {collection_type!r}. Allowed: {allowed}.")
        if col_cls is HourlyContinuousCollection:
            created_col = col_cls(hdr, values)
        else:
            parsed_dts = [_parse_datetime_item(dt) for dt in (datetimes or [])]
            if not parsed_dts and col_cls is DailyCollection:
                parsed_dts = [Date(dt.month, dt.day, dt.leap_year) for dt in hdr.analysis_period.datetimes[::24 * hdr.analysis_period.timestep]]
            elif not parsed_dts and col_cls is MonthlyCollection:
                parsed_dts = sorted(set(hdr.analysis_period.months_int))
            elif not parsed_dts and col_cls is MonthlyPerHourCollection:
                parsed_dts = hdr.analysis_period.moys_per_hour if hasattr(hdr.analysis_period, "moys_per_hour") else hdr.analysis_period.datetimes[:len(values)]
            elif not parsed_dts:
                parsed_dts = hdr.analysis_period.datetimes[:len(values)]
            created_col = col_cls(hdr, values, parsed_dts)
        return _persist_collection_result(
            garden_root_path=garden_root_path,
            collection=created_col,
            identifier=identifier or f"created_{slugify_name(hdr.data_type.name)}",
            source={"producer": "LB_Analyze_Data_Collection", "action": "create"},
            message="DataCollection created and persisted.",
            return_data_collection=return_data_collection,
        )

    if act == "inspect":
        col = _resolve_single_collection(
            garden_root_path=garden_root_path,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
        )
        summary_view = _inspect_collection(
            col,
            percentiles=percentiles,
            histogram_bins=histogram_bins,
            include_values=include_values,
            max_values=max_values,
        )
        summary_view["garden_target"] = manifest.target()
        result: dict[str, Any] = {
            "summary_view": summary_view,
            "report": make_report(status="ok", message="DataCollection inspected."),
        }
        if return_data_collection:
            result["data_collection"] = col.to_dict()
        return result

    if act == "filter":
        multi_inputs: list[Any] = []
        for item in data_collections or []:
            multi_inputs.append(_coerce_collection(item))
        for tgt in data_collection_targets or []:
            multi_inputs.append(load_data_collection(garden_root=garden_root_path, data_collection_target=tgt))
        if multi_inputs:
            if not conditional_statement:
                raise ValueError(
                    "conditional_statement is required when filtering multiple collections."
                )
            filtered_list = BaseCollection.filter_collections_by_statement(
                multi_inputs, conditional_statement
            )
            base_id = slugify_name(identifier or "filtered_collection")
            saved_list = [
                save_data_collection(
                    garden_root=garden_root_path,
                    data_collection=col,
                    identifier=f"{base_id}_{idx}",
                    source={
                        "producer": "LB_Analyze_Data_Collection",
                        "action": "filter",
                        "filter_type": "filter_collections_by_statement",
                        "conditional_statement": conditional_statement,
                    },
                )
                for idx, col in enumerate(filtered_list, start=1)
            ]
            return {
                "target": saved_list[0]["target"],
                "targets": [s["target"] for s in saved_list],
                "data_collection_targets": [s["target"] for s in saved_list],
                "artifacts": [s["artifact"] for s in saved_list],
                "persistence_receipts": [s["persistence_receipt"] for s in saved_list],
                "summary_view": {
                    "garden_target": manifest.target(),
                    "filter_type": "filter_collections_by_statement",
                    "conditional_statement": conditional_statement,
                    "collection_count": len(saved_list),
                    "collections": [s["summary_view"] for s in saved_list],
                },
                "report": make_report(
                    status="ok",
                    message=f"Filtered {len(saved_list)} aligned DataCollections.",
                ),
            }

        col = _resolve_single_collection(
            garden_root_path=garden_root_path,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
        )
        inferred = (filter_type or "").strip().lower()
        if not inferred:
            if analysis_period is not None:
                inferred = "analysis_period"
            elif hoys is not None:
                inferred = "hoys"
            elif greater_than is not None or less_than is not None:
                inferred = "range"
            elif conditional_statement is not None:
                inferred = "conditional_statement"
            elif pattern is not None:
                inferred = "pattern"
            else:
                raise ValueError(
                    "Provide filter_type or one of analysis_period, hoys, greater_than/less_than, "
                    "conditional_statement, or pattern."
                )

        if inferred == "analysis_period":
            ap_obj = analysis_period_from_input(analysis_period)
            if ap_obj is None:
                raise ValueError("analysis_period is required for filter_type='analysis_period'.")
            out_col = col.filter_by_analysis_period(ap_obj)
        elif inferred == "hoys":
            if hoys is None:
                raise ValueError("hoys is required for filter_type='hoys'.")
            out_col = col.filter_by_hoys(hoys)
        elif inferred == "range":
            gt = float("-inf") if greater_than is None else float(greater_than)
            lt = float("inf") if less_than is None else float(less_than)
            out_col = col.filter_by_range(greater_than=gt, less_than=lt)
        elif inferred == "conditional_statement":
            if not conditional_statement:
                raise ValueError("conditional_statement is required for filter_type='conditional_statement'.")
            out_col = col.filter_by_conditional_statement(conditional_statement)
        elif inferred == "pattern":
            if pattern is None:
                raise ValueError("pattern is required for filter_type='pattern'.")
            out_col = col.filter_by_pattern(pattern)
        else:
            raise ValueError(
                f"Unsupported filter_type {inferred!r}. Allowed: analysis_period, hoys, range, conditional_statement, pattern."
            )

        return _persist_collection_result(
            garden_root_path=garden_root_path,
            collection=out_col,
            identifier=identifier or f"filtered_{inferred}",
            source={"producer": "LB_Analyze_Data_Collection", "action": "filter", "filter_type": inferred},
            message=f"DataCollection filtered by {inferred}.",
            return_data_collection=return_data_collection,
            extra_summary={"filter_type": inferred},
        )

    if act == "degree_days":
        col = _resolve_single_collection(
            garden_root_path=garden_root_path,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
        )
        op_alias = str(operation or "degree_days").strip().lower()
        if op_alias not in {"degree_days", "heating_degree_days", "cooling_degree_days"}:
            raise ValueError(
                f"Unsupported degree_days operation {operation!r}. "
                "Allowed: degree_days, heating_degree_days, cooling_degree_days."
            )
        return _calculate_degree_days(
            garden_root_path=garden_root_path,
            manifest=manifest,
            col=col,
            source_action="degree_days",
            op_alias=op_alias,
            degree_day_type=degree_day_type,
            base_temperature=base_temperature,
            heating_base_temperature=heating_base_temperature,
            cooling_base_temperature=cooling_base_temperature,
            identifier=identifier,
        )

    if act == "aggregate":
        col = _resolve_single_collection(
            garden_root_path=garden_root_path,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
        )
        op = str(operation or "monthly").strip().lower()
        if op in {"degree_days", "heating_degree_days", "cooling_degree_days"}:
            return _calculate_degree_days(
                garden_root_path=garden_root_path,
                manifest=manifest,
                col=col,
                source_action="aggregate",
                op_alias=op,
                degree_day_type=degree_day_type,
                base_temperature=base_temperature,
                heating_base_temperature=heating_base_temperature,
                cooling_base_temperature=cooling_base_temperature,
                identifier=identifier,
            )
        method = str(aggregation_method or "average").strip().lower()
        if method == "avg":
            method = "average"

        if op in {"daily", "monthly", "monthly_per_hour"}:
            if method == "average":
                out_col = getattr(col, f"average_{op}")()
            elif method == "total":
                out_col = getattr(col, f"total_{op}")()
            elif method == "percentile":
                out_col = getattr(col, f"percentile_{op}")(percentile_value)
            else:
                raise ValueError("aggregation_method must be one of: average, avg, total, percentile.")
        elif op == "to_time_aggregated":
            out_col = col.to_time_aggregated()
        elif op == "to_time_rate_of_change":
            out_col = col.to_time_rate_of_change()
        elif op == "interpolate_holes":
            dup = col.duplicate()
            res_col = dup.interpolate_holes()
            out_col = res_col if res_col is not None else dup
        elif op == "convert_to_culled_timestep":
            dup = col.duplicate()
            res_col = dup.convert_to_culled_timestep(timestep=timestep)
            out_col = res_col if res_col is not None else dup
        elif op == "interpolate_to_timestep":
            out_col = col.interpolate_to_timestep(timestep=timestep, cumulative=cumulative)
        elif op == "normalize_by_area":
            if area is None or area <= 0:
                raise ValueError("area must be a positive number for operation='normalize_by_area'.")
            out_col = col.normalize_by_area(area, area_unit)
        else:
            raise ValueError(
                f"Unsupported aggregate operation {op!r}. Allowed: daily, monthly, monthly_per_hour, "
                "to_time_aggregated, to_time_rate_of_change, interpolate_holes, "
                "convert_to_culled_timestep, interpolate_to_timestep, normalize_by_area, "
                "degree_days, heating_degree_days, cooling_degree_days."
            )
        return _persist_collection_result(
            garden_root_path=garden_root_path,
            collection=out_col,
            identifier=identifier or f"agg_{op}",
            source={"producer": "LB_Analyze_Data_Collection", "action": "aggregate", "operation": op},
            message=f"DataCollection aggregated with {op}.",
            return_data_collection=return_data_collection,
            extra_summary={"operation": op, "aggregation_method": method},
        )

    if act == "math":
        col = _resolve_single_collection(
            garden_root_path=garden_root_path,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
        )
        op = str(operation or "").strip().lower()
        op_alias = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide"}.get(op, op)

        if op_alias == "to_unit":
            if not target_unit:
                raise ValueError("target_unit is required for operation='to_unit'.")
            out_col = col.to_unit(target_unit)
        elif op_alias == "to_ip":
            out_col = col.to_ip()
        elif op_alias == "to_si":
            out_col = col.to_si()
        elif op_alias in {"add", "subtract", "multiply", "divide"}:
            has_other = other_data_collection is not None or other_data_collection_target is not None
            if (scalar is None) == (not has_other):
                raise ValueError(
                    f"operation={op!r} requires exactly one of scalar or other_data_collection/other_data_collection_target."
                )
            operand = (
                float(scalar)
                if scalar is not None
                else _resolve_single_collection(
                    garden_root_path=garden_root_path,
                    data_collection=other_data_collection,
                    data_collection_target=other_data_collection_target,
                    field_name="other_data_collection",
                )
            )
            if op_alias == "add":
                out_col = col + operand
            elif op_alias == "subtract":
                out_col = col - operand
            elif op_alias == "multiply":
                out_col = col * operand
            else:
                out_col = col / operand
        elif op_alias in {"degree_days", "heating_degree_days", "cooling_degree_days"}:
            return _calculate_degree_days(
                garden_root_path=garden_root_path,
                manifest=manifest,
                col=col,
                source_action="math",
                op_alias=op_alias,
                degree_day_type=degree_day_type,
                base_temperature=base_temperature,
                heating_base_temperature=heating_base_temperature,
                cooling_base_temperature=cooling_base_temperature,
                identifier=identifier,
            )
        else:
            raise ValueError(
                f"Unsupported math operation {op!r}. Allowed: to_unit, to_ip, to_si, "
                "add (+), subtract (-), multiply (*), divide (/), degree_days, "
                "heating_degree_days, cooling_degree_days."
            )

        return _persist_collection_result(
            garden_root_path=garden_root_path,
            collection=out_col,
            identifier=identifier or f"math_{op_alias}",
            source={"producer": "LB_Analyze_Data_Collection", "action": "math", "operation": op_alias},
            message=f"DataCollection math '{op_alias}' completed.",
            return_data_collection=return_data_collection,
            extra_summary={"operation": op_alias},
        )

    raise ValueError(
        f"Unsupported action {action!r}. Allowed: import, create, inspect, filter, aggregate, math, degree_days."
    )


__all__ = [
    "DATA_COLLECTION_ARTIFACT_TYPE",
    "DATA_COLLECTION_CSV_ARTIFACT_TYPE",
    "DATA_COLLECTION_PKL_ARTIFACT_TYPE",
    "DATA_COLLECTION_TARGET_TYPE",
    "analyze_data_collection",
    "collection_from_dict",
    "data_collection_summary",
    "export_data_collection_file",
    "load_data_collection",
    "save_data_collection",
]
