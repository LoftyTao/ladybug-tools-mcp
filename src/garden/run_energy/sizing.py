"""Compact EnergyPlus sizing-result reader."""

from __future__ import annotations

from typing import Any

from garden.run_energy.annual import _run_id_from_target_or_value, _run_record_by_id
from garden.run_energy.results import _garden_root, _sql_result
from ladybug_tools_mcp.contracts.report import make_report


def _matches(value: str, query: str | None) -> bool:
    return query is None or query.strip().lower() in value.lower()


def _blocker(run_id: str, reason: str) -> dict[str, Any]:
    return {
        "summary_view": {"run_id": run_id, "sizing_count": 0},
        "energy_blocker": {
            "reason": reason,
            "recommended_next_tools": ["EP_poll_simulation", "EP_list_run_outputs"],
        },
        "report": make_report(status="blocked", message=reason),
    }


def read_energy_sizing(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    zone: str | None = None,
    component: str | None = None,
    sizing_category: str | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Read compact zone and component sizing from a completed Energy run."""
    if max_results <= 0:
        raise ValueError("max_results must be positive.")
    category = (
        sizing_category.strip().lower().replace("-", "_").replace(" ", "_")
        if sizing_category
        else None
    )
    if category not in {None, "zone", "component", "heating", "cooling", "zone_heating", "zone_cooling"}:
        raise ValueError(
            "sizing_category must be zone, component, heating, or cooling."
        )
    root = _garden_root(garden_root)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    if record.get("status") != "completed":
        return _blocker(resolved_run_id, "Sizing results require a completed Energy run.")
    try:
        _, sql_path, sql, _ = _sql_result(
            garden_root=root, run_target=run_target, run_id=run_id
        )
    except (FileNotFoundError, ValueError) as exc:
        return _blocker(resolved_run_id, f"Sizing SQL is unavailable: {exc}")
    zones = []
    if category in {None, "zone", "heating", "zone_heating", "cooling", "zone_cooling"}:
        zone_sizes = (
            sql.zone_heating_sizes
            if category in {"heating", "zone_heating"}
            else sql.zone_cooling_sizes
            if category in {"cooling", "zone_cooling"}
            else [*sql.zone_heating_sizes, *sql.zone_cooling_sizes]
        )
        for item in zone_sizes:
            data = item.to_dict()
            if _matches(str(data.get("zone_name", "")), zone):
                zones.append(data)
    components = []
    if category in {None, "component"}:
        for item in sql.component_sizes:
            data = item.to_dict()
            if _matches(str(data.get("component_name", "")), component):
                components.append(data)
    total = len(zones) + len(components)
    if not total:
        return _blocker(resolved_run_id, "No sizing results matched the requested filters.")
    return {
        "run_target": record.get("target") or run_target,
        "summary_view": {
            "run_id": resolved_run_id,
            "sql_path": str(sql_path.relative_to(root)).replace("\\", "/"),
            "zone_result_count": len(zones),
            "component_result_count": len(components),
            "result_count": total,
            "filters": {"zone": zone, "component": component, "sizing_category": category},
        },
        "zone_sizing": zones[:max_results],
        "component_sizing": components[:max_results],
        "results_truncated": total > max_results,
        "report": make_report(status="ok", message=f"Read EnergyPlus sizing for run {resolved_run_id}."),
    }
