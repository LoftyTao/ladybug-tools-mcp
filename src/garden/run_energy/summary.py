"""Intent-driven compact summaries for EnergyPlus run results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee_energy.result.emissions import (
    emissions_from_sql,
    emissions_region,
    future_electricity_emissions,
)
from honeybee_energy.result.generation import (
    generation_data_from_sql,
    generation_summary_from_sql,
)
from honeybee_energy.result.loadbalance import LoadBalance

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.run_energy.annual import (
    _absolute_output_path,
    _energy_run_result_evidence,
    _outputs_map,
    _run_id_from_target_or_value,
    _run_record_by_id,
)
from garden.run_energy.results import (
    _available_output_infos,
    _data_collections,
    _garden_root,
    _resolve_honeybee_model_for_run,
    _resolve_run_output_file,
    _sql_result,
)
from ladybug_tools_mcp.contracts import make_report

SUMMARY_KINDS = {
    "energy_use",
    "loads",
    "peaks",
    "sizing",
    "load_balance",
    "unmet_hours",
    "tabular",
    "emissions",
    "generation",
    "zsz",
    "rdd",
    "osw",
}
_PERIODS = {
    "annual": "annual",
    "year": "annual",
    "yearly": "annual",
    "monthly": "monthly",
    "month": "monthly",
}
_LOAD_CATEGORIES = ("heating", "cooling", "lighting", "equipment", "dhw")
# Prioritized non-overlapping output variable allowlists per end-use sub-source
# so Ideal Loads supply vs zone, sensible vs total, and lights/equipment electricity
# vs thermal gains are never double-counted.
_LOAD_ALLOWLISTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "heating": (
        (
            "Zone Ideal Loads Supply Air Total Heating Energy",
            "Zone Ideal Loads Zone Total Heating Energy",
            "Zone Ideal Loads Supply Air Sensible Heating Energy",
            "Baseboard Total Heating Energy",
            "Heating Coil Heating Energy",
            "Heating Coil Electricity Energy",
            "Heating Coil NaturalGas Energy",
            "Boiler NaturalGas Energy",
            "Boiler Electricity Energy",
            "District Heating Water Energy",
        ),
    ),
    "cooling": (
        (
            "Zone Ideal Loads Supply Air Total Cooling Energy",
            "Zone Ideal Loads Zone Total Cooling Energy",
            "Zone Ideal Loads Supply Air Sensible Cooling Energy",
            "Cooling Coil Total Cooling Energy",
            "Cooling Coil Electricity Energy",
            "Chiller Electricity Energy",
            "District Cooling Water Energy",
        ),
    ),
    "lighting": (
        (
            "Zone Lights Electricity Energy",
            "Zone Lights Total Heating Energy",
        ),
    ),
    "equipment": (
        (
            "Zone Electric Equipment Electricity Energy",
            "Zone Electric Equipment Total Heating Energy",
        ),
        (
            "Zone Gas Equipment NaturalGas Energy",
            "Zone Gas Equipment Total Heating Energy",
        ),
        (
            "Zone Other Equipment Total Heating Energy",
        ),
    ),
    "dhw": (
        (
            "Water Use Equipment Heating Energy",
            "Water Use Equipment Zone Sensible Heat Gain Energy",
            "Water Heater Electricity Energy",
            "Water Heater NaturalGas Energy",
        ),
    ),
}
_LOAD_OUTPUTS = (
    "Zone Ideal Loads Supply Air Total Heating Energy",
    "Zone Ideal Loads Supply Air Total Cooling Energy",
    "Zone Lights Electricity Energy",
    "Zone Electric Equipment Electricity Energy",
    "Water Use Equipment Heating Energy",
)
_PEAK_RATE_CANDIDATES = {
    "heating": (
        "Zone Ideal Loads Supply Air Total Heating Rate",
        "Zone Ideal Loads Zone Total Heating Rate",
        "Zone Air System Sensible Heating Rate",
    ),
    "cooling": (
        "Zone Ideal Loads Supply Air Total Cooling Rate",
        "Zone Ideal Loads Zone Total Cooling Rate",
        "Zone Air System Sensible Cooling Rate",
    ),
}
_PEAK_ENERGY_CANDIDATES = {
    "heating": (
        "Zone Ideal Loads Supply Air Total Heating Energy",
        "Zone Ideal Loads Zone Total Heating Energy",
    ),
    "cooling": (
        "Zone Ideal Loads Supply Air Total Cooling Energy",
        "Zone Ideal Loads Zone Total Cooling Energy",
    ),
}
_ENERGY_UNITS = {"wh": ("Wh", 0.001), "kwh": ("kWh", 1), "mwh": ("MWh", 1000)}
_POWER_UNITS = {"w": ("W", 1), "kw": ("kW", 1000)}


def _kind(value: str) -> str:
    result = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if result not in SUMMARY_KINDS:
        allowed = ", ".join(sorted(SUMMARY_KINDS))
        raise ValueError(f"summary_kind must be one of: {allowed}.")
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
    if isinstance(collection, (int, float)) and not isinstance(collection, bool):
        return [float(collection)]
    return [
        float(value)
        for value in list(getattr(collection, "values", []) or [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]


def _monthly(collection: Any) -> list[float]:
    if isinstance(collection, (int, float)) and not isinstance(collection, bool):
        return []
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
    if not metadata:
        return False
    return query.lower() in " ".join(map(str, metadata.values())).lower()


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
    if kind in {"peaks", "sizing", "zsz"}:
        arguments = {
            "mode": "output_request",
            "identifier": "energy_summary_peaks",
            "summary_reports": ["AllSummary"],
            "reporting_frequency": "Annual",
            "include_sqlite": True,
        }
        required = ["epluszsz.csv", "eplusout.sql"]
    elif kind in {"load_balance"}:
        arguments = {
            "mode": "output_request",
            "identifier": "energy_summary_load_balance",
            "presets": ["energy_balance", "gains_and_losses", "zone_energy_use", "surface_energy_flow"],
            "reporting_frequency": "Monthly" if period == "monthly" else "Hourly",
            "include_sqlite": True,
        }
        required = ["eplusout.sql", "Zone Ideal Loads Supply Air Total Heating Energy"]
    elif kind in {"unmet_hours"}:
        arguments = {
            "mode": "output_request",
            "identifier": "energy_summary_unmet_hours",
            "presets": ["unmet_hours"],
            "summary_reports": ["AllSummary"],
            "reporting_frequency": "Hourly",
            "include_sqlite": True,
        }
        required = ["eplusout.sql", "Zone Heating Setpoint Not Met Time", "Zone Cooling Setpoint Not Met Time"]
    elif kind in {"emissions", "generation", "tabular"}:
        arguments = {
            "mode": "output_request",
            "identifier": f"energy_summary_{kind}",
            "summary_reports": ["AllSummary"],
            "reporting_frequency": "Hourly",
            "include_sqlite": True,
        }
        required = ["eplusout.sql"]
    else:
        arguments = {
            "mode": "output_request",
            "identifier": f"energy_summary_{kind}",
            "presets": ["zone_energy_use"],
            "reporting_frequency": "Monthly" if period == "monthly" else "Annual",
            "include_sqlite": True,
        }
        required = list(_LOAD_OUTPUTS)
    return {
        "tool": "EP_Create_Simulation_Parameter",
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
        "run_target": run_target,
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
        "recommended_next_tools": ["EP_Create_Simulation_Parameter", "EP_Start_Simulation"],
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
    evidence = _energy_run_result_evidence(garden_root=root, run_id=run_id, record=record)
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
            "result_evidence": evidence,
            "final_answer_ready": evidence["final_answer_ready"],
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
    available_set = {str(name) for name in (getattr(sql, "available_outputs", ()) or ())}
    units = {str(item["output_name"]): str(item.get("unit") or "kWh") for item in infos if item.get("output_name")}
    matched: dict[str, list[str]] = {category: [] for category in _LOAD_CATEGORIES}
    for category in _LOAD_CATEGORIES:
        for candidate_group in _LOAD_ALLOWLISTS[category]:
            selected_output = next((name for name in candidate_group if name in available_set), None)
            if selected_output is not None:
                matched[category].append(selected_output)
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


def _coincident_from_collections(
    collections: list[Any],
    *,
    query: str | None,
    scale: float = 1.0,
) -> tuple[float | None, int | None, int]:
    matched = [coll for coll in collections if _in_scope(coll, query)]
    if not matched:
        return None, None, 0
    step_counts = [len(getattr(coll, "values", []) or []) for coll in matched]
    step_count = min(step_counts) if step_counts else 0
    if step_count <= 0:
        return None, None, len(matched)
    totals = [
        sum(
            float(coll.values[idx]) * scale
            for coll in matched
            if isinstance(coll.values[idx], (int, float)) and not isinstance(coll.values[idx], bool)
        )
        for idx in range(step_count)
    ]
    peak_val = max(totals)
    return peak_val, totals.index(peak_val), len(matched)


def _compute_coincident_peak(
    *,
    root: Path,
    record: dict[str, Any],
    sql: Any,
    category: str,
    query: str | None,
) -> tuple[float | None, int | None, str | None, str | None, int]:
    from honeybee_energy.result.zsz import ZSZ

    try:
        zsz_path = _resolve_run_output_file(
            root,
            record,
            "zsz",
            ("openstudio/run/epluszsz.csv", "epluszsz.csv"),
        )
        zsz = ZSZ(str(zsz_path))
        colls = list(zsz.heating_load_data if category == "heating" else zsz.cooling_load_data)
        peak_w, step_idx, count = _coincident_from_collections(colls, query=query, scale=1.0)
        if peak_w is not None:
            return peak_w, step_idx, "zsz", "epluszsz.csv", count
    except (OSError, ValueError, AssertionError, IndexError):
        pass

    available = set(getattr(sql, "available_outputs", ()) or ())
    for rate_name in _PEAK_RATE_CANDIDATES[category]:
        if rate_name in available:
            colls = _data_collections(sql, rate_name, None)
            peak_w, step_idx, count = _coincident_from_collections(colls, query=query, scale=1.0)
            if peak_w is not None:
                return peak_w, step_idx, "sql_hourly_rate", rate_name, count

    for energy_name in _PEAK_ENERGY_CANDIDATES[category]:
        if energy_name in available:
            colls = _data_collections(sql, energy_name, None)
            if not colls or isinstance(colls[0], (int, float)):
                continue
            header = getattr(colls[0], "header", None)
            ap = getattr(header, "analysis_period", None) if header else None
            timestep = getattr(ap, "timestep", 1) or 1
            if "hourly" in type(colls[0]).__name__.lower():
                unit_str = str(getattr(header, "unit", "") or "").lower()
                scale = 1000.0 * float(timestep) if unit_str == "kwh" else 1.0
                peak_w, step_idx, count = _coincident_from_collections(colls, query=query, scale=scale)
                if peak_w is not None:
                    return peak_w, step_idx, "sql_hourly_energy", energy_name, count

    return None, None, None, None, 0


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
    sql = None
    sql_error: str | None = None
    try:
        _, _sql_path, sql, _ = _sql_result(garden_root=root, run_target=run_target, run_id=run_id)
    except (OSError, ValueError) as exc:
        sql_error = str(exc)

    query = _scope_query(scope)
    metrics: list[dict[str, Any]] = []
    details: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    warnings: list[str] = []
    if sql_error is not None:
        warnings.append(f"Energy sizing SQL is unavailable ({sql_error}); attempting ZSZ fallback.")

    size_groups = {
        "heating": getattr(sql, "zone_heating_sizes", ()) if sql is not None else (),
        "cooling": getattr(sql, "zone_cooling_sizes", ()) if sql is not None else (),
    }
    for category, items in size_groups.items():
        selected = [
            item.to_dict()
            for item in (items or ())
            if not query or query.lower() in str(getattr(item, "zone_name", "")).lower()
        ]
        values = [
            float(item.get("final_design_load", item.get("calculated_design_load")))
            for item in selected
            if isinstance(item.get("final_design_load", item.get("calculated_design_load")), (int, float))
        ]
        coincident_w, peak_step_idx, coincident_src, coincident_output, coincident_zones = (
            _compute_coincident_peak(
                root=root,
                record=record,
                sql=sql,
                category=category,
                query=query,
            )
        )
        if not values and coincident_w is None:
            missing.append(category)
            warnings.append(f"No sizing or hourly peak result supports the {category} peak summary for the requested scope.")
            continue

        unit = "W"
        conversion = {"source_unit": "W", "target_unit": "W", "factor": 1.0}
        converted_values: list[float] = []
        for value in values:
            converted, unit, conversion, warning = _convert(value, "W", unit_preference)
            converted_values.append(converted)
            if warning and warning not in warnings:
                warnings.append(warning)

        coincident_converted = None
        if coincident_w is not None:
            coincident_converted, unit, conversion, warning = _convert(coincident_w, "W", unit_preference)
            if warning and warning not in warnings:
                warnings.append(warning)

        max_zone_peak = max(converted_values) if converted_values else None
        non_coincident_sum = sum(converted_values) if converted_values else None
        primary_value = max_zone_peak if max_zone_peak is not None else coincident_converted
        metric = {
            "name": f"{category}_peak",
            "value": primary_value,
            "max_zone_peak": max_zone_peak,
            "coincident_peak": coincident_converted,
            "non_coincident_sum": non_coincident_sum,
            "coincident_source": coincident_src,
            "coincident_output": coincident_output,
            "coincident_zone_count": coincident_zones,
            "peak_step_index": peak_step_idx,
            "unit": unit,
            "period": "annual",
            "source_outputs": ["epluszsz.csv", "eplusout.sql"],
            "scope": scope,
            "aggregation": (
                "maximum final_design_load across matching sizing zones "
                "with coincident building peak"
            ),
            "conversion": conversion,
            "range": (
                {"minimum": min(converted_values), "maximum": max(converted_values), "unit": unit}
                if converted_values
                else {"minimum": coincident_converted, "maximum": coincident_converted, "unit": unit}
            ),
            "count": len(selected) if selected else coincident_zones,
        }
        metrics.append(metric)
        if coincident_converted is not None:
            metrics.append(
                {
                    "name": f"{category}_coincident_peak",
                    "value": coincident_converted,
                    "unit": unit,
                    "period": "annual",
                    "source_outputs": [coincident_output or "epluszsz.csv"],
                    "scope": scope,
                    "peak_step_index": peak_step_idx,
                    "zone_count": coincident_zones,
                    "aggregation": f"coincident sum across matching zones from {coincident_src}",
                    "conversion": conversion,
                }
            )
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
            reason=sql_error or "No zone sizing or ZSZ result is available for the requested peak summary.",
            required=["epluszsz.csv", "eplusout.sql"],
            warnings=warnings,
        )
    peak_values = {
        metric["name"].removesuffix("_peak"): metric
        for metric in metrics
        if metric["name"].endswith("_peak") and not metric["name"].endswith("_coincident_peak")
    }
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
            "method": "maximum_and_coincident_sum",
            "conversion": "Max zone peak uses final_design_load; coincident peak sums zone profiles per timestep from ZSZ or hourly SQL.",
            "time_range": _time_range(period),
        },
        warnings=warnings,
        extra={
            "peaks": peak_values,
            "peak_details": details,
            "missing_categories": missing,
            "output_request_suggestion": _suggestion("peaks", period) if missing else None,
            "interpretation": {
                **_context(root, record),
                "aggregation": "Reports both max zone final_design_load and coincident building peak across matching zones.",
            },
        },
    )


def _load_balance(
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
            kind="load_balance",
            period=period,
            scope=scope,
            reason=f"Energy SQL is unavailable for load_balance: {exc}",
            required=["eplusout.sql"],
        )
    try:
        model = _resolve_honeybee_model_for_run(root, record)
    except (OSError, ValueError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="load_balance",
            period=period,
            scope=scope,
            reason=f"LoadBalance requires a Honeybee Model matching the simulation run: {exc}",
            required=["eplusout.sql"],
        )

    query = _scope_query(scope)
    rooms = (
        [
            room
            for room in model.rooms
            if query.lower() in room.identifier.lower() or query.lower() in str(room.zone).lower()
        ]
        if query
        else list(model.rooms)
    )
    if not rooms:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="load_balance",
            period=period,
            scope=scope,
            reason="No Honeybee Model rooms matched the requested scope for load_balance.",
            required=["eplusout.sql"],
        )
    try:
        if query:
            lb = LoadBalance.from_sql_file_rooms(rooms, str(sql_path), units=model.units)
        else:
            lb = LoadBalance.from_sql_file(model, str(sql_path))
    except Exception as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="load_balance",
            period=period,
            scope=scope,
            reason=f"Could not construct LoadBalance from SQL: {exc}",
            required=["eplusout.sql"],
        )

    term_defs = (
        ("heating", lb.heating),
        ("cooling", lb.cooling),
        ("lighting", lb.lighting),
        ("electric_equip", lb.electric_equip),
        ("gas_equip", lb.gas_equip),
        ("process", lb.process),
        ("service_hot_water", lb.service_hot_water),
        ("people", lb.people),
        ("solar", lb.solar),
        ("infiltration", lb.infiltration),
        ("mech_ventilation", lb.mech_ventilation),
        ("nat_ventilation", lb.nat_ventilation),
        ("opaque_conduction", lb.opaque_conduction),
        ("window_conduction", lb.window_conduction),
        ("wall_conduction", lb.wall_conduction),
        ("roof_conduction", lb.roof_conduction),
        ("floor_conduction", lb.floor_conduction),
        ("storage", lb.storage),
    )
    metrics: list[dict[str, Any]] = []
    terms_map: dict[str, Any] = {}
    warnings: list[str] = []
    floor_area = lb.floor_area or None
    for term_name, coll in term_defs:
        if coll is None:
            continue
        source_unit = str(getattr(getattr(coll, "header", None), "unit", None) or "kWh")
        if period == "annual":
            raw_val = sum(_numeric(coll))
            converted, unit, conversion, warning = _convert(raw_val, source_unit, unit_preference)
            value: Any = converted
        else:
            monthly_vals = _monthly(coll)
            if not monthly_vals:
                continue
            converted_list: list[float] = []
            unit = source_unit
            conversion = {"source_unit": source_unit, "target_unit": source_unit, "factor": 1.0}
            warning = None
            for mv in monthly_vals:
                c_val, unit, conversion, warning = _convert(mv, source_unit, unit_preference)
                converted_list.append(c_val)
            value = converted_list
        if warning and warning not in warnings:
            warnings.append(warning)
        metric: dict[str, Any] = {
            "name": term_name,
            "value": value,
            "unit": unit,
            "period": period,
            "source_output": "eplusout.sql",
            "aggregation": "LoadBalance thermal balance term",
            "conversion": conversion,
        }
        if floor_area and period == "annual" and isinstance(value, (int, float)):
            metric["normalized_value"] = value / floor_area
            metric["normalized_unit"] = f"{unit}/m²"
        metrics.append(metric)
        terms_map[term_name] = metric

    if not metrics:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="load_balance",
            period=period,
            scope=scope,
            reason="SQL file contains no matching LoadBalance energy balance outputs.",
            required=["eplusout.sql"],
        )

    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="load_balance",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "sql")],
        aggregation={
            "method": "honeybee_energy.result.loadbalance.LoadBalance",
            "conversion": "Thermal balance gains are positive and cooling/heat losses are negative.",
            "time_range": _time_range(period, list(getattr(sql, "run_period_names", ()) or ())),
        },
        warnings=warnings,
        extra={
            "load_balance": terms_map,
            "matched_room_count": len(lb.rooms),
            "floor_area": floor_area,
            "units_system": lb.units,
        },
    )


def _unmet_hours(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    period: str,
    scope: str | dict[str, Any] | None,
    zone: str | None,
) -> dict[str, Any]:
    try:
        _, _sql_path, sql, _ = _sql_result(garden_root=root, run_target=run_target, run_id=run_id)
    except (OSError, ValueError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="unmet_hours",
            period=period,
            scope=scope,
            reason=f"Energy SQL is unavailable for unmet_hours: {exc}",
            required=["eplusout.sql"],
        )

    query = zone if zone is not None else _scope_query(scope)
    warnings: list[str] = []
    facility_summary: dict[str, Any] = {}
    zone_tabular: dict[str, dict[str, Any]] = {}
    tolerance: dict[str, Any] = {}

    if period == "annual":
        try:
            summary_tbl = sql.tabular_data_by_name(
                "Comfort and Setpoint Not Met Summary",
                j_to_kwh=False,
                report_name="AnnualBuildingUtilityPerformanceSummary",
            )
            for row_name, vals in summary_tbl.items():
                if vals:
                    facility_summary[str(row_name)] = vals[0]
        except Exception:
            pass
        try:
            tol_tbl = sql.tabular_data_by_name(
                "Setpoint Not Met Criteria",
                j_to_kwh=False,
                report_name="AnnualBuildingUtilityPerformanceSummary",
            )
            for row_name, vals in tol_tbl.items():
                if vals:
                    tolerance[str(row_name)] = vals[0]
        except Exception:
            pass
        try:
            zone_tbl = sql.tabular_data_by_name(
                "Time Setpoint Not Met",
                j_to_kwh=False,
                report_name="SystemSummary",
            )
            cols = list(
                sql.tabular_column_names(
                    "Time Setpoint Not Met", report_name="SystemSummary"
                )
            )
            for row_name, vals in zone_tbl.items():
                r_name = str(row_name)
                if r_name == "Facility":
                    for idx, col in enumerate(cols):
                        if idx < len(vals):
                            facility_summary.setdefault(f"Facility {col}", vals[idx])
                    continue
                if query and query.lower() not in r_name.lower():
                    continue
                zone_tabular[r_name] = {
                    cols[idx]: vals[idx]
                    for idx in range(min(len(cols), len(vals)))
                }
        except Exception:
            pass

    hourly_var_names = (
        ("heating", "Zone Heating Setpoint Not Met Time"),
        ("cooling", "Zone Cooling Setpoint Not Met Time"),
        ("occupied_heating", "Zone Heating Setpoint Not Met While Occupied Time"),
        ("occupied_cooling", "Zone Cooling Setpoint Not Met While Occupied Time"),
    )
    available = set(getattr(sql, "available_outputs", ()) or ())
    hourly_zones: dict[str, dict[str, Any]] = {}
    hourly_totals: dict[str, Any] = {}
    for key, var_name in hourly_var_names:
        if var_name not in available:
            continue
        colls = [
            coll
            for coll in _data_collections(sql, var_name, None)
            if _in_scope(coll, query)
        ]
        if not colls:
            continue
        for coll in colls:
            z_name = _collection_scope(coll) or "Facility"
            z_entry = hourly_zones.setdefault(z_name, {})
            if period == "annual":
                z_entry[key] = sum(_numeric(coll))
            else:
                z_entry[key] = _monthly(coll)
        if period == "annual":
            hourly_totals[key] = sum(sum(_numeric(coll)) for coll in colls)
        else:
            monthly_sum: list[float] = []
            for coll in colls:
                m_vals = _monthly(coll)
                if len(monthly_sum) < len(m_vals):
                    monthly_sum.extend([0.0] * (len(m_vals) - len(monthly_sum)))
                for idx, val in enumerate(m_vals):
                    monthly_sum[idx] += val
            hourly_totals[key] = monthly_sum

    if not facility_summary and not zone_tabular and not hourly_totals:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="unmet_hours",
            period=period,
            scope=scope,
            reason=(
                "SQL contains neither 'Time Setpoint Not Met' tabular reports "
                "nor hourly setpoint-not-met output variables."
            ),
            required=["eplusout.sql"],
        )

    metrics: list[dict[str, Any]] = []
    if period == "annual":
        heating_val = facility_summary.get(
            "Facility During Heating",
            hourly_totals.get("heating"),
        )
        cooling_val = facility_summary.get(
            "Facility During Cooling",
            hourly_totals.get("cooling"),
        )
        occ_heating_val = facility_summary.get(
            "Time Setpoint Not Met During Occupied Heating",
            facility_summary.get(
                "Facility During Occupied Heating",
                hourly_totals.get("occupied_heating"),
            ),
        )
        occ_cooling_val = facility_summary.get(
            "Time Setpoint Not Met During Occupied Cooling",
            facility_summary.get(
                "Facility During Occupied Cooling",
                hourly_totals.get("occupied_cooling"),
            ),
        )
        for name, val in (
            ("heating_unmet_hours", heating_val),
            ("cooling_unmet_hours", cooling_val),
            ("occupied_heating_unmet_hours", occ_heating_val),
            ("occupied_cooling_unmet_hours", occ_cooling_val),
        ):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                metrics.append(
                    {
                        "name": name,
                        "value": float(val),
                        "unit": "hr",
                        "period": "annual",
                        "source_output": "sql",
                        "aggregation": "SQL tabular and/or hourly unmet hours",
                    }
                )
    else:
        for key, vals in hourly_totals.items():
            metrics.append(
                {
                    "name": f"{key}_unmet_hours",
                    "value": vals,
                    "unit": "hr",
                    "period": "monthly",
                    "months": list(range(1, len(vals) + 1)),
                    "source_output": "sql",
                    "aggregation": "monthly sum across matching zones",
                }
            )

    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="unmet_hours",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "sql")],
        aggregation={
            "method": "tabular_and_hourly_sql",
            "conversion": "Values are reported in hours (hr).",
            "time_range": _time_range(period),
        },
        warnings=warnings,
        extra={
            "unmet_hours": {
                "facility": facility_summary,
                "zones": zone_tabular,
                "hourly_totals": hourly_totals,
                "hourly_zones": hourly_zones,
                "tolerance": tolerance,
            },
        },
    )


def _resolve_emissions_location(
    root: Path,
    record: dict[str, Any],
    loc: Any,
) -> Any:
    """Resolve a US-state-bearing Location for eGrid emissions lookup."""
    import re
    from ladybug.epw import EPW
    from ladybug.location import Location

    if loc is not None and emissions_region(loc) is not None:
        return loc
    if loc is not None:
        city_text = str(getattr(loc, "city", "") or "")
        state_match = re.search(
            r"(?:^|[\s,])([A-Z]{2})(?:\s+(?:USA|US))?\s*$",
            city_text.strip(),
        )
        if state_match:
            try:
                candidate = Location.from_dict(
                    {
                        **loc.to_dict(),
                        "state": state_match.group(1),
                        "country": "USA",
                    }
                )
            except Exception:
                candidate = None
            if candidate is not None and emissions_region(candidate) is not None:
                return candidate
    epw_rel = record.get("epw_path")
    if isinstance(epw_rel, str) and epw_rel.strip():
        epw_candidate = Path(epw_rel)
        if not epw_candidate.is_absolute():
            epw_candidate = root / epw_candidate
        if epw_candidate.is_file():
            try:
                epw_loc = EPW(str(epw_candidate)).location
            except Exception:
                epw_loc = None
            if epw_loc is not None and emissions_region(epw_loc) is not None:
                return epw_loc
    return loc


def _emissions(
    *,
    root: Path,
    manifest_target: dict[str, Any],
    record: dict[str, Any],
    run_target: dict[str, Any] | None,
    run_id: str,
    period: str,
    scope: str | dict[str, Any] | None,
    electricity_emissions: float | None,
    emissions_year: int,
) -> dict[str, Any]:
    if period != "annual":
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="emissions",
            period=period,
            scope=scope,
            reason="The emissions summary is annual only.",
            required=["eplusout.sql"],
        )
    try:
        _, sql_path, sql, _ = _sql_result(garden_root=root, run_target=run_target, run_id=run_id)
    except (OSError, ValueError) as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="emissions",
            period=period,
            scope=scope,
            reason=f"Energy SQL is unavailable for emissions: {exc}",
            required=["eplusout.sql"],
        )

    loc = _resolve_emissions_location(root, record, getattr(sql, "location", None))
    region = emissions_region(loc) if loc is not None else None
    grid_factor = electricity_emissions
    if grid_factor is None:
        if loc is None or region is None:
            return _blocked(
                root=root,
                manifest_target=manifest_target,
                record=record,
                run_target=run_target,
                run_id=run_id,
                kind="emissions",
                period=period,
                scope=scope,
                reason=(
                    "Could not infer US eGrid electricity emissions factor from SQL location; "
                    "pass electricity_emissions (kg CO2/MWh) explicitly."
                ),
                required=["eplusout.sql"],
            )
        try:
            grid_factor = float(future_electricity_emissions(loc, year=int(emissions_year)))
        except (ValueError, TypeError) as exc:
            return _blocked(
                root=root,
                manifest_target=manifest_target,
                record=record,
                run_target=run_target,
                run_id=run_id,
                kind="emissions",
                period=period,
                scope=scope,
                reason=(
                    f"emissions_year {emissions_year!r} is unsupported for auto lookup ({exc}); "
                    "use an even year from 2020 to 2050 or pass electricity_emissions explicitly."
                ),
                required=["eplusout.sql"],
            )

    try:
        payload = emissions_from_sql(str(sql_path), float(grid_factor))
    except Exception as exc:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="emissions",
            period=period,
            scope=scope,
            reason=f"Failed to compute emissions from SQL: {exc}",
            required=["eplusout.sql"],
        )

    metrics = [
        {
            "name": "carbon_intensity",
            "value": payload["carbon_intensity"],
            "unit": "kgCO2/m²·yr",
            "period": "annual",
            "source_output": "sql",
            "aggregation": "emissions_from_sql",
        },
        {
            "name": "total_carbon",
            "value": payload["total_carbon"],
            "unit": "kgCO2",
            "period": "annual",
            "source_output": "sql",
            "aggregation": "emissions_from_sql",
        },
    ]
    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="emissions",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "sql")],
        aggregation={
            "method": "honeybee_energy.result.emissions.emissions_from_sql",
            "conversion": f"electricity_emissions={grid_factor} kgCO2/MWh",
            "time_range": _time_range(period),
        },
        warnings=[],
        extra={
            "emissions": {
                **payload,
                "end_uses": dict(payload.get("end_uses") or {}),
                "sources": dict(payload.get("sources") or {}),
                "electricity_emissions_kg_per_mwh": float(grid_factor),
                "emissions_year": emissions_year if electricity_emissions is None else None,
                "emissions_region": region,
            },
            "carbon_intensity": payload["carbon_intensity"],
            "total_carbon": payload["total_carbon"],
        },
    )


def _generation(
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
            kind="generation",
            period=period,
            scope=scope,
            reason=f"Energy SQL is unavailable for generation: {exc}",
            required=["eplusout.sql"],
        )

    warnings: list[str] = []
    try:
        gen_tbl = sql.tabular_data_by_name("Electric Loads Satisfied")
    except Exception:
        gen_tbl = {}
    summary_dict = generation_summary_from_sql(str(sql_path))
    prod_coll, cons_coll = generation_data_from_sql(str(sql_path))

    if not gen_tbl and prod_coll is None and cons_coll is None:
        return _blocked(
            root=root,
            manifest_target=manifest_target,
            record=record,
            run_target=run_target,
            run_id=run_id,
            kind="generation",
            period=period,
            scope=scope,
            reason=(
                "SQL contains neither 'Electric Loads Satisfied' tabular data "
                "nor electricity generation timeseries outputs."
            ),
            required=["eplusout.sql"],
        )

    metrics: list[dict[str, Any]] = []
    if period == "annual":
        for key in (
            "total_production",
            "total_consumption",
            "production_used_on_site",
            "production_surplus_sold",
            "consumption_purchased",
        ):
            converted, unit, conversion, warning = _convert(
                float(summary_dict[key]), "kWh", unit_preference
            )
            if warning and warning not in warnings:
                warnings.append(warning)
            metrics.append(
                {
                    "name": key,
                    "value": converted,
                    "unit": unit,
                    "period": "annual",
                    "source_output": "sql",
                    "aggregation": "generation_summary_from_sql",
                    "conversion": conversion,
                }
            )
    else:
        for key, coll in (("production", prod_coll), ("consumption", cons_coll)):
            if coll is None or isinstance(coll, (int, float)):
                continue
            m_vals = _monthly(coll)
            if not m_vals:
                continue
            converted_vals: list[float] = []
            unit = "kWh"
            conversion = {"source_unit": "kWh", "target_unit": "kWh", "factor": 1.0}
            for mv in m_vals:
                c_val, unit, conversion, warning = _convert(mv, "kWh", unit_preference)
                converted_vals.append(c_val)
                if warning and warning not in warnings:
                    warnings.append(warning)
            metrics.append(
                {
                    "name": key,
                    "value": converted_vals,
                    "unit": unit,
                    "period": "monthly",
                    "months": list(range(1, len(converted_vals) + 1)),
                    "source_output": "sql",
                    "aggregation": "monthly sum from generation_data_from_sql",
                    "conversion": conversion,
                }
            )
        if not metrics:
            return _blocked(
                root=root,
                manifest_target=manifest_target,
                record=record,
                run_target=run_target,
                run_id=run_id,
                kind="generation",
                period=period,
                scope=scope,
                reason="Monthly generation timeseries outputs were not found in SQL.",
                required=["Facility Total Produced Electricity Energy", "Facility Net Purchased Electricity Energy"],
            )

    return _result(
        manifest_target=manifest_target,
        run_target=record.get("target") or run_target,
        run_id=run_id,
        kind="generation",
        period=period,
        scope=scope,
        metrics=metrics,
        sources=[_source(root, record, "sql")],
        aggregation={
            "method": "honeybee_energy.result.generation",
            "conversion": "Negative values represent electricity consumption or grid purchases.",
            "time_range": _time_range(period),
        },
        warnings=warnings,
        extra={"generation": summary_dict},
    )


def summarize_energy_results(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    energy_run_target: dict[str, Any] | None = None,
    summary_kind: str = "energy_use",
    scope: str | dict[str, Any] | None = None,
    period: str = "annual",
    unit_preference: str | None = None,
    run_id: str | None = None,
    zone: str | None = None,
    component: str | None = None,
    sizing_category: str | None = None,
    max_results: int = 50,
    table_name: str | None = None,
    report_name: str | None = None,
    j_to_kwh: bool = True,
    electricity_emissions: float | None = None,
    emissions_year: int = 2030,
    include_values: bool = False,
    max_values: int = 24,
) -> dict[str, Any]:
    """Return one compact intent-driven summary for an Energy run."""
    if (
        run_target is not None
        and energy_run_target is not None
        and run_target != energy_run_target
    ):
        raise ValueError("Provide run_target or energy_run_target, or ensure they match.")
    resolved_target = run_target if run_target is not None else energy_run_target
    kind = _kind(summary_kind)
    if kind == "sizing":
        from garden.run_energy.results import read_energy_sizing

        sizing_zone = zone if zone is not None else _scope_query(scope)
        sizing = read_energy_sizing(
            garden_root=garden_root,
            run_target=resolved_target,
            run_id=run_id,
            zone=sizing_zone,
            component=component,
            sizing_category=sizing_category,
            max_results=max_results,
        )
        sizing["summary_kind"] = "sizing"
        sizing["energy_run_target"] = sizing.get("run_target")
        sizing.setdefault("summary_view", {})["summary_kind"] = "sizing"
        return sizing

    normalized_period = _period(period)
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id = _run_id_from_target_or_value(run_target=resolved_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)

    if kind == "tabular":
        from garden.run_energy.results import read_energy_tabular_data

        try:
            payload = read_energy_tabular_data(
                garden_root=garden_root,
                run_target=resolved_target,
                run_id=run_id,
                table_name=table_name,
                report_name=report_name,
                table_query=_scope_query(scope) if table_name is None else None,
                j_to_kwh=j_to_kwh,
                max_results=max_results,
            )
        except (OSError, ValueError) as exc:
            return _blocked(
                root=root,
                manifest_target=manifest.target(),
                record=record,
                run_target=resolved_target,
                run_id=resolved_run_id,
                kind="tabular",
                period=normalized_period,
                scope=scope,
                reason=str(exc),
                required=["eplusout.sql"],
            )
        payload["summary_kind"] = "tabular"
        payload["energy_run_target"] = payload.get("run_target")
        payload.setdefault("summary_view", {})["summary_kind"] = "tabular"
        return payload

    if kind == "zsz":
        from garden.run_energy.results import read_energy_zsz

        try:
            payload = read_energy_zsz(
                garden_root=garden_root,
                run_target=resolved_target,
                run_id=run_id,
                zone=zone if zone is not None else _scope_query(scope),
                include_values=include_values,
                max_values=max_values,
                max_results=max_results,
            )
        except (OSError, ValueError) as exc:
            return _blocked(
                root=root,
                manifest_target=manifest.target(),
                record=record,
                run_target=resolved_target,
                run_id=resolved_run_id,
                kind="zsz",
                period=normalized_period,
                scope=scope,
                reason=str(exc),
                required=["epluszsz.csv"],
            )
        payload["summary_kind"] = "zsz"
        payload["energy_run_target"] = payload.get("run_target")
        payload.setdefault("summary_view", {})["summary_kind"] = "zsz"
        return payload

    if kind == "rdd":
        from garden.run_energy.results import read_energy_rdd

        try:
            payload = read_energy_rdd(
                garden_root=garden_root,
                run_target=resolved_target,
                run_id=run_id,
                query=zone if zone is not None else _scope_query(scope),
                max_results=max_results,
            )
        except (OSError, ValueError) as exc:
            return _blocked(
                root=root,
                manifest_target=manifest.target(),
                record=record,
                run_target=resolved_target,
                run_id=resolved_run_id,
                kind="rdd",
                period=normalized_period,
                scope=scope,
                reason=str(exc),
                required=["eplusout.rdd"],
            )
        payload["summary_kind"] = "rdd"
        payload["energy_run_target"] = payload.get("run_target")
        payload.setdefault("summary_view", {})["summary_kind"] = "rdd"
        return payload

    if kind == "osw":
        from garden.run_energy.results import read_energy_osw

        try:
            payload = read_energy_osw(
                garden_root=garden_root,
                run_target=resolved_target,
                run_id=run_id,
            )
        except (OSError, ValueError) as exc:
            return _blocked(
                root=root,
                manifest_target=manifest.target(),
                record=record,
                run_target=resolved_target,
                run_id=resolved_run_id,
                kind="osw",
                period=normalized_period,
                scope=scope,
                reason=str(exc),
                required=["out.osw"],
            )
        payload["summary_kind"] = "osw"
        payload["energy_run_target"] = payload.get("run_target")
        payload.setdefault("summary_view", {})["summary_kind"] = "osw"
        return payload

    arguments = {
        "root": root,
        "manifest_target": manifest.target(),
        "record": record,
        "run_target": resolved_target,
        "run_id": resolved_run_id,
        "period": normalized_period,
        "scope": scope,
        "unit_preference": unit_preference,
    }
    if kind == "energy_use":
        return _energy_use(**arguments)
    if kind == "loads":
        return _loads(**arguments)
    if kind == "peaks":
        return _peaks(**arguments)
    if kind == "load_balance":
        return _load_balance(**arguments)
    if kind == "unmet_hours":
        return _unmet_hours(
            root=root,
            manifest_target=manifest.target(),
            record=record,
            run_target=resolved_target,
            run_id=resolved_run_id,
            period=normalized_period,
            scope=scope,
            zone=zone,
        )
    if kind == "emissions":
        return _emissions(
            root=root,
            manifest_target=manifest.target(),
            record=record,
            run_target=resolved_target,
            run_id=resolved_run_id,
            period=normalized_period,
            scope=scope,
            electricity_emissions=electricity_emissions,
            emissions_year=emissions_year,
        )
    return _generation(**arguments)
