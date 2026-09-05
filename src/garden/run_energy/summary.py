"""Intent-driven compact summaries for EnergyPlus run results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.run_energy.annual import (
    _absolute_output_path,
    _outputs_map,
    _run_id_from_target_or_value,
    _run_record_by_id,
)
from garden.run_energy.results import (
    _available_output_infos,
    _data_collections,
    _garden_root,
    _sql_result,
)
from ladybug_tools_mcp.contracts.report import make_report

SUMMARY_KINDS = {"energy_use", "loads", "peaks"}
_PERIODS = {"annual": "annual", "year": "annual", "yearly": "annual", "monthly": "monthly", "month": "monthly"}
_LOAD_CATEGORIES = ("heating", "cooling", "lighting", "equipment", "dhw")
_LOAD_OUTPUTS = (
    "Zone Ideal Loads Supply Air Total Heating Energy",
    "Zone Ideal Loads Supply Air Total Cooling Energy",
    "Zone Lights Electricity Energy",
    "Zone Electric Equipment Electricity Energy",
    "Water Use Equipment Heating Energy",
)
_ENERGY_UNITS = {"wh": ("Wh", 0.001), "kwh": ("kWh", 1), "mwh": ("MWh", 1000)}
_POWER_UNITS = {"w": ("W", 1), "kw": ("kW", 1000)}


def _kind(value: str) -> str:
    result = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if result not in SUMMARY_KINDS:
        raise ValueError("summary_kind must be energy_use, loads, or peaks.")
    return result


def _period(value: str) -> str:
    result = str(value or "annual").strip().lower().replace("-", "_")
    if result not in _PERIODS:
        raise ValueError("period must be annual or monthly.")
    return _PERIODS[result]


def _scope_query(scope: str | dict[str, Any] | None) -> str | None:
    if scope is None:
        return None
    if isinstance(scope, str):
        return scope.strip() or None
    if isinstance(scope, dict):
        for key in ("zone", "identifier", "query", "name"):
            if scope.get(key):
                return str(scope[key]).strip()
    raise ValueError("scope must be a string, object with zone/identifier/query/name, or null.")


def _source(root: Path, record: dict[str, Any], file_name: str, output_name: str | None = None) -> dict[str, Any]:
    output = _outputs_map(record).get(file_name) or {}
    path = output.get("path")
    exists = bool(output.get("exists") and path)
    if path:
        candidate = (root / str(path)).resolve()
        try:
            candidate.relative_to(root)
            exists = exists and candidate.is_file()
        except ValueError:
            exists = False
    return {
        "name": output_name or file_name,
        "file_name": file_name,
        "output_name": output_name,
        "path": path,
        "exists": exists,
    }


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result = []
    for source in sources:
        key = (source.get("file_name"), source.get("output_name"), source.get("path"))
        if key not in seen:
            seen.add(key)
            result.append(source)
    return result


def _convert(value: float, source_unit: str, preference: str | None) -> tuple[float, str, dict[str, Any], str | None]:
    source_key = source_unit.strip().lower().replace(" ", "")
    if not preference:
        return value, source_unit, {"source_unit": source_unit, "target_unit": source_unit, "factor": 1.0}, None
    preference_key = preference.strip().lower().replace(" ", "")
    eui = "/m" in source_key or "/ft" in source_key
    units = _ENERGY_UNITS if eui or source_key in _ENERGY_UNITS else _POWER_UNITS if source_key in _POWER_UNITS else {}
    if eui:
        source_key = source_key.split("/", 1)[0]
        target_key = preference_key.split("/", 1)[0]
        target_info = _ENERGY_UNITS.get(target_key)
        if target_info:
            target_unit = f"{target_info[0]}/m²·yr"
        else:
            target_unit = ""
    else:
        target_info = units.get(preference_key)
        target_unit = target_info[0] if target_info else ""
    source_info = units.get(source_key)
    if not source_info or not target_info:
        return (
            value,
            source_unit,
            {"source_unit": source_unit, "target_unit": source_unit, "factor": 1.0},
            f"Unit preference {preference!r} cannot convert source unit {source_unit!r}; source unit retained.",
        )
    factor = source_info[1] / target_info[1]
    return value * factor, target_unit, {
        "source_unit": source_unit,
        "target_unit": target_unit,
        "factor": factor,
    }, None


def _numeric(collection: Any) -> list[float]:
    return [
        float(value)
        for value in list(getattr(collection, "values", []) or [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]


def _monthly(collection: Any) -> list[float]:
    if "monthly" in type(collection).__name__.lower():
        return _numeric(collection)
    method = getattr(collection, "total_monthly", None)
    return _numeric(method()) if callable(method) else []


def _collection_scope(collection: Any) -> str | None:
    metadata = dict(getattr(getattr(collection, "header", None), "metadata", {}) or {})
    for key in ("Zone", "zone", "Room", "room", "System", "system"):
        if metadata.get(key) is not None:
            return str(metadata[key])
    return None


def _in_scope(collection: Any, query: str | None) -> bool:
    if not query:
        return True
    metadata = dict(getattr(getattr(collection, "header", None), "metadata", {}) or {})
    return query.lower() in " ".join(map(str, metadata.values())).lower()


def _category(output_name: str) -> str | None:
    value = output_name.lower()
    if "energy" not in value and "consumption" not in value:
        return None
    if any(token in value for token in ("water use", "water heater", "water heating", "service hot water")):
        return "dhw"
    if "light" in value:
        return "lighting"
    if any(token in value for token in ("electric equipment", "gas equipment", "other equipment")):
        return "equipment"
    if "cool" in value:
        return "cooling"
    if "heat" in value:
        return "heating"
    return None


def _time_range(period: str, names: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"period": period}
    if period == "monthly":
        result["months"] = list(range(1, 13))
    if names:
        result["run_period_names"] = names
    return result


def _context(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(_absolute_output_path(root, record, "eui").read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    return {
        "cop": {"value": None, "applied": False, "reason": "COP was not inferred from result files."},
        "floor_area_m2": payload.get("total_floor_area"),
        "floor_area_source": "eui.json" if payload.get("total_floor_area") is not None else None,
        "multiplier": {"value": None, "applied": False, "reason": "No additional multiplier was applied to EnergyPlus results."},
    }


def _suggestion(kind: str, period: str) -> dict[str, Any]:
    if kind == "peaks":
        arguments = {
            "identifier": "energy_summary_peaks",
            "summary_reports": ["AllSummary"],
            "reporting_frequency": "Annual",
            "include_sqlite": True,
        }
        required = ["epluszsz.csv", "eplusout.sql"]
    else:
        arguments = {
            "identifier": f"energy_summary_{kind}",
            "presets": ["zone_energy_use"],
            "reporting_frequency": "Monthly" if period == "monthly" else "Annual",
            "include_sqlite": True,
        }
        required = list(_LOAD_OUTPUTS)
    return {
        "tool": "EP_create_output_request",
        "arguments": arguments,
        "required_outputs": required,
        "next_run_argument": "output_request_target",
    }


def _result(
    *,
    manifest_target: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    kind: str,
    period: str,
    scope: str | dict[str, Any] | None,
    metrics: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    aggregation: dict[str, Any],
    warnings: list[str],
    status: str = "ok",
    message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    time_range = aggregation.pop("time_range", _time_range(period))
    units = sorted({str(metric["unit"]) for metric in metrics if metric.get("unit")})
    filters = {"scope": scope, "period": period}
    summary = {
        "garden_target": manifest_target,
        "run_id": run_id,
        "summary_kind": kind,
        "status": status,
        "period": period,
        "time_range": time_range,
        "filters": filters,
        "units": units,
        "metrics": metrics,
        "source_outputs": sources,
        "aggregation": aggregation,
        "warnings": warnings,
    }
    result: dict[str, Any] = {
        "energy_run_target": run_target,
        "summary_kind": kind,
        "status": status,
        "run_id": run_id,
        "period": period,
        "time_range": time_range,
        "filters": filters,
        "units": units,
        "metrics": metrics,
        "source_outputs": sources,
        "aggregation": aggregation,
        "warnings": warnings,
        "summary_view": summary,
        "report": make_report(status=status, message=message or f"Energy {kind} summary returned for run {run_id}.", warnings=warnings),
    }
    if extra:
        result.update(extra)
        summary.update(extra)
    return result


def _blocked(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    kind: str,
    period: str,
    scope: str | dict[str, Any] | None,
    reason: str,
    required: list[str],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    suggestion = _suggestion(kind, period)
    warning_list = [*(warnings or []), reason]
    available = [str(item["name"]) for item in record.get("outputs", []) if item.get("name") and item.get("exists")]
    blocker = {
        "status": "missing_result_support",
        "reason": reason,
        "run_status": record.get("status"),
        "required_outputs": required,
        "available_output_names": available,
        "output_request_suggestion": suggestion,
        "recommended_next_tools": ["EP_create_output_request", "EP_start_simulation"],
        "no_implicit_rerun": True,
    }
    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind=kind,
        period=period,
        scope=scope,
        metrics=[],
        sources=[_source(root, record, name) for name in ("eui", "sql", "zsz")],
        aggregation={"method": "not_available", "conversion": "not_available"},
        warnings=warning_list,
        status="blocked",
        message=reason,
        extra={"energy_blocker": blocker, "output_request_suggestion": suggestion},
    )


def _energy_use(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    period: str,
    scope: str | dict[str, Any] | None,
    unit_preference: str | None,
) -> dict[str, Any]:
    if period != "annual":
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="energy_use",
            period=period,
            scope=scope,
            reason="The energy_use summary is available only for annual EUI output.",
            required=["eui.json"],
        )
    try:
        payload = json.loads(_absolute_output_path(root, record, "eui").read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="energy_use",
            period=period,
            scope=scope,
            reason=f"Annual EUI output is unavailable: {exc}",
            required=["eui.json"],
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("eui"), (int, float)):
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="energy_use",
            period=period,
            scope=scope,
            reason="The annual EUI output has no numeric eui value.",
            required=["eui.json"],
        )
    warnings = ["The annual EUI output is whole-building; scope was recorded but not applied."] if scope is not None else []
    metrics: list[dict[str, Any]] = []
    eui_unit = "kWh/m²·yr"

    def add(name: str, value: Any, source_unit: str, metric_type: str, **fields: Any) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return
        converted, unit, conversion, warning = _convert(float(value), source_unit, unit_preference)
        if warning:
            warnings.append(warning)
        metrics.append({
            "name": name,
            "value": converted,
            "unit": unit,
            "period": "annual",
            "source_output": "eui",
            "metric_type": metric_type,
            "aggregation": "read from eui.json",
            "conversion": conversion,
            **fields,
        })

    add("eui", payload["eui"], eui_unit, "energy_use_intensity")
    add("total_energy", payload.get("total_energy"), "kWh", "total_energy")
    if isinstance(payload.get("total_floor_area"), (int, float)):
        metrics.append({
            "name": "total_floor_area",
            "value": payload["total_floor_area"],
            "unit": "m²",
            "period": "annual",
            "source_output": "eui",
            "metric_type": "floor_area",
            "aggregation": "read from eui.json",
            "conversion": {"source_unit": "m²", "target_unit": "m²", "factor": 1.0},
        })
    end_uses = payload.get("end_uses") if isinstance(payload.get("end_uses"), dict) else {}
    for name, value in end_uses.items():
        add(str(name).lower().replace(" ", "_"), value, eui_unit, "end_use_energy_intensity", end_use=str(name))
    summary_end_uses = {item["end_use"]: item["value"] for item in metrics if item.get("end_use")}
    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="energy_use",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "eui")],
        aggregation={"method": "read", "conversion": "EUI and end-use values are reported as stored.", "time_range": _time_range(period)},
        warnings=warnings,
        extra={
            "eui": metrics[0]["value"],
            "end_uses": summary_end_uses,
            "total_energy": next((item["value"] for item in metrics if item["name"] == "total_energy"), None),
            "total_floor_area": payload.get("total_floor_area"),
            "interpretation": {**_context(root, record), "aggregation": "EUI and end-use values are read without recomputation."},
        },
    )


def _loads(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    period: str,
    scope: str | dict[str, Any] | None,
    unit_preference: str | None,
) -> dict[str, Any]:
    try:
        _, sql_path, sql, _ = _sql_result(garden_root=root, run_target=run_target, run_id=run_id)
    except (OSError, ValueError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="loads",
            period=period,
            scope=scope,
            reason=f"Energy SQL is unavailable for load summarization: {exc}",
            required=list(_LOAD_OUTPUTS),
        )
    infos = _available_output_infos(
        available_outputs=list(getattr(sql, "available_outputs", []) or []),
        available_outputs_info=list(getattr(sql, "available_outputs_info", []) or []),
    )
    units = {str(item["output_name"]): str(item.get("unit") or "kWh") for item in infos if item.get("output_name")}
    matched: dict[str, list[str]] = {category: [] for category in _LOAD_CATEGORIES}
    for output_name in getattr(sql, "available_outputs", ()) or ():
        category = _category(str(output_name))
        if category:
            matched[category].append(str(output_name))
    query = _scope_query(scope)
    metrics: list[dict[str, Any]] = []
    warnings: list[str] = []
    missing: list[str] = []
    sources = [_source(root, record, "sql")]
    for category in _LOAD_CATEGORIES:
        series: list[tuple[str, Any, str | None]] = []
        for output_name in matched[category]:
            series.extend(
                (output_name, collection, _collection_scope(collection))
                for collection in _data_collections(sql, output_name, None)
                if _in_scope(collection, query)
            )
        if not series:
            missing.append(category)
            warnings.append(f"No existing SQL output supports the {category} load summary.")
            continue
        output_names = sorted({item[0] for item in series})
        sources.extend(
            _source(root, record, "sql", output_name=output_name)
            | {"path": to_posix_relative(sql_path, root), "exists": True}
            for output_name in output_names
        )
        source_unit = next((units.get(name) for name in output_names if units.get(name)), "kWh")
        if period == "annual":
            value = sum(sum(_numeric(collection)) for _, collection, _ in series)
            converted, unit, conversion, warning = _convert(value, source_unit, unit_preference)
        else:
            monthly_values: list[float] = []
            for _, collection, _ in series:
                values = _monthly(collection)
                if len(monthly_values) < len(values):
                    monthly_values.extend([0.0] * (len(values) - len(monthly_values)))
                for index, current in enumerate(values):
                    monthly_values[index] += current
            if not monthly_values:
                missing.append(category)
                warnings.append(f"SQL outputs for {category} have no monthly values.")
                continue
            converted_values = []
            converted = None
            unit = source_unit
            conversion = None
            warning = None
            for value in monthly_values:
                converted, unit, conversion, warning = _convert(value, source_unit, unit_preference)
                converted_values.append(converted)
            value = converted_values
        if warning:
            warnings.append(warning)
        metric = {
            "name": category,
            "value": value,
            "unit": unit,
            "period": period,
            "source_outputs": output_names,
            "scope": scope,
            "series_count": len(series),
            "series_scopes": sorted({label for _, _, label in series if label}),
            "aggregation": "sum across matching SQL DataCollection series" if period == "annual" else "sum by calendar month",
            "conversion": conversion,
        }
        if period == "monthly":
            metric["months"] = list(range(1, len(value) + 1))
        metrics.append(metric)
    if not metrics:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="loads",
            period=period,
            scope=scope,
            reason="No requested load category has a readable SQL DataCollection.",
            required=list(_LOAD_OUTPUTS),
            warnings=warnings,
        )
    load_values = {metric["name"]: metric for metric in metrics}
    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="loads",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=_dedupe_sources(sources),
        aggregation={
            "method": "sum",
            "conversion": "SQL source units are retained unless unit_preference is convertible.",
            "time_range": _time_range(period, list(getattr(sql, "run_period_names", ()) or ())),
        },
        warnings=warnings,
        extra={
            "loads": load_values,
            "missing_categories": missing,
            "output_request_suggestion": _suggestion("loads", period) if missing else None,
            "interpretation": {**_context(root, record), "aggregation": "Load values are summed across matching SQL DataCollection series."},
        },
    )


def _peaks(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    period: str,
    scope: str | dict[str, Any] | None,
    unit_preference: str | None,
) -> dict[str, Any]:
    if period != "annual":
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="peaks",
            period=period,
            scope=scope,
            reason="The peaks summary is an annual design-day result; monthly peak data is unavailable from ZSZ sizing output.",
            required=["epluszsz.csv", "eplusout.sql"],
        )
    try:
        _, _sql_path, sql, _ = _sql_result(garden_root=root, run_target=run_target, run_id=run_id)
    except (OSError, ValueError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="peaks",
            period=period,
            scope=scope,
            reason=f"Energy sizing SQL is unavailable for peak summarization: {exc}",
            required=["epluszsz.csv", "eplusout.sql"],
        )
    query = _scope_query(scope)
    metrics: list[dict[str, Any]] = []
    details: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    warnings: list[str] = []
    for category, items in {
        "heating": getattr(sql, "zone_heating_sizes", ()) or (),
        "cooling": getattr(sql, "zone_cooling_sizes", ()) or (),
    }.items():
        selected = [
            item.to_dict()
            for item in items
            if not query or query.lower() in str(getattr(item, "zone_name", "")).lower()
        ]
        values = [
            float(item.get("final_design_load", item.get("calculated_design_load")))
            for item in selected
            if isinstance(item.get("final_design_load", item.get("calculated_design_load")), (int, float))
        ]
        if not values:
            missing.append(category)
            warnings.append(f"No sizing result supports the {category} peak summary for the requested scope.")
            continue
        converted_values = []
        for value in values:
            converted, unit, conversion, warning = _convert(value, "W", unit_preference)
            converted_values.append(converted)
        if warning:
            warnings.append(warning)
        metric = {
            "name": f"{category}_peak",
            "value": max(converted_values),
            "unit": unit,
            "period": "annual",
            "source_outputs": ["epluszsz.csv", "eplusout.sql"],
            "scope": scope,
            "aggregation": "maximum final_design_load across matching sizing zones",
            "conversion": conversion,
            "range": {"minimum": min(converted_values), "maximum": max(converted_values), "unit": unit},
            "count": len(selected),
        }
        metrics.append(metric)
        details[category] = [
            {
                "zone_name": item.get("zone_name"),
                "load_type": item.get("load_type"),
                "value": converted_values[index],
                "unit": unit,
                "design_day_name": item.get("design_day_name"),
                "peak_date_time": item.get("peak_date_time"),
            }
            for index, item in enumerate(selected)
        ]
    if not metrics:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="peaks",
            period=period,
            scope=scope,
            reason="No zone sizing result is available for the requested peak summary.",
            required=["epluszsz.csv", "eplusout.sql"],
            warnings=warnings,
        )
    peak_values = {metric["name"].removesuffix("_peak"): metric for metric in metrics}
    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="peaks",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "zsz"), _source(root, record, "sql")],
        aggregation={
            "method": "maximum",
            "conversion": "Peak values use final_design_load from sizing results.",
            "time_range": _time_range(period),
        },
        warnings=warnings,
        extra={
            "peaks": peak_values,
            "peak_details": details,
            "missing_categories": missing,
            "output_request_suggestion": _suggestion("peaks", period) if missing else None,
            "interpretation": {**_context(root, record), "aggregation": "Peak values use the maximum final_design_load across matching sizing zones."},
        },
    )


def summarize_energy_results(
    *,
    garden_root: str,
    energy_run_target: dict[str, Any] | None = None,
    summary_kind: str,
    scope: str | dict[str, Any] | None = None,
    period: str = "annual",
    unit_preference: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return one compact intent-driven summary for an Energy run."""
    kind = _kind(summary_kind)
    normalized_period = _period(period)
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id = _run_id_from_target_or_value(run_target=energy_run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    arguments = {
        "root": root,
        "manifest_target": manifest.target(),
        "record": record,
        "run_target": energy_run_target,
        "run_id": resolved_run_id,
        "period": normalized_period,
        "scope": scope,
        "unit_preference": unit_preference,
    }
    if kind == "energy_use":
        return _energy_use(**arguments)
    if kind == "loads":
        return _loads(**arguments)
    return _peaks(**arguments)
