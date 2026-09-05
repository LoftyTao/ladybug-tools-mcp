"""Compact readers for native Radiance daylight compliance results."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.metrics import (
    _garden_root,
    _require_completed,
    _run_record,
)
from garden.radiance.visual import _validate_run_target_garden


COMPLIANCE_RECIPES = {
    "leed-daylight-option-two",
    "annual-daylight-en17037",
    "leed-daylight-option-one",
    "well-daylight",
    "breeam-daylight-4b",
}
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50

_OVERVIEW_OUTPUTS = {
    "leed-daylight-option-two": ("credit-summary",),
    "annual-daylight-en17037": ("summary",),
    "leed-daylight-option-one": ("credit-summary",),
    "breeam-daylight-4b": ("summary",),
}
_SPACE_OUTPUTS = {
    "leed-daylight-option-two": ("space-summary",),
    "annual-daylight-en17037": ("summary-grid",),
    "leed-daylight-option-one": ("space-summary",),
    "breeam-daylight-4b": ("program-summary",),
}
_VISUALIZATION_OUTPUTS = {
    "leed-daylight-option-two": ("visualization",),
    "annual-daylight-en17037": ("visualization-en17037", "visualization-metrics"),
    "leed-daylight-option-one": ("visualization",),
    "well-daylight": ("visualization",),
    "breeam-daylight-4b": ("visualization",),
}


def _output_entries(
    garden_root: Path,
    record: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    """Resolve the compact output inventory recorded by the run ledger."""
    raw_outputs = record.get("outputs") or []

    entries: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    for raw in raw_outputs:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        path_value = raw.get("path")
        entry = {
            "name": name,
            "path": str(path_value) if path_value else None,
            "exists": bool(raw.get("exists", False)),
        }
        if path_value:
            try:
                path = Path(str(path_value)).expanduser()
                path = path.resolve() if path.is_absolute() else (garden_root / path).resolve()
                path.relative_to(garden_root)
            except (OSError, ValueError):
                entry["path"] = None
                entry["exists"] = False
            else:
                entry["exists"] = path.exists()
                if path.exists():
                    entry["path"] = to_posix_relative(path, garden_root)
                    paths[name] = path
        if "required" in raw:
            entry["required"] = bool(raw["required"])
        entries.append(entry)
    return entries, paths


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read compliance JSON output: {path.name}: {exc}") from exc


def _output_for(
    output_paths: dict[str, Path],
    output_names: tuple[str, ...],
) -> tuple[str, Path] | None:
    for name in output_names:
        path = output_paths.get(name)
        if path is not None:
            return name, path
    return None


def _overview(
    recipe: str,
    output_paths: dict[str, Path],
    warnings: list[str],
) -> Any:
    if recipe == "well-daylight":
        result: dict[str, Any] = {}
        for key, output_name in (
            ("l01", "l01-summary"),
            ("l06", "l06-summary"),
            ("well_version", "well-version"),
        ):
            path = output_paths.get(output_name)
            if path is None:
                warnings.append(f"Compliance output was not found: {output_name}.")
                continue
            result[key] = _read_json(path)
        return result

    selected = _output_for(output_paths, _OVERVIEW_OUTPUTS.get(recipe, ()))
    if selected is None:
        warnings.append("No aggregate compliance summary output was found.")
        return None
    return _read_json(selected[1])


def _csv_value(value: str | None) -> Any:
    text = (value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    if not math.isfinite(number):
        return text
    return int(number) if number.is_integer() else number


def _json_rows(recipe: str, payload: Any) -> list[dict[str, Any]]:
    if recipe in {"annual-daylight-en17037", "breeam-daylight-4b"}:
        return [dict(item) for item in payload if isinstance(item, dict)]
    if recipe == "leed-daylight-option-one" and isinstance(payload, dict):
        return [
            {"space_id": identifier, **value}
            for identifier, value in payload.items()
            if isinstance(value, dict)
        ]
    return []


def _space_page(
    recipe: str,
    output_paths: dict[str, Path],
    *,
    page: int,
    page_size: int,
    warnings: list[str],
) -> dict[str, Any]:
    selected = _output_for(output_paths, _SPACE_OUTPUTS.get(recipe, ()))
    if selected is None:
        return {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "page_count": 0,
            "has_next": False,
        }

    path = selected[1]
    start = (page - 1) * page_size
    items: list[dict[str, Any]] = []
    total = 0
    try:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if start <= total < start + page_size:
                        items.append(
                            {
                                key: _csv_value(value)
                                for key, value in row.items()
                            }
                        )
                    total += 1
        else:
            rows = _json_rows(recipe, _read_json(path))
            total = len(rows)
            items = rows[start : start + page_size]
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        warnings.append(f"Could not read space summary output {selected[0]}: {exc}")

    page_count = math.ceil(total / page_size) if total else 0
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "page_count": page_count,
        "has_next": page < page_count,
        "source_output": selected[0],
    }


def _visualization_target(
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    output_paths: dict[str, Path],
) -> dict[str, Any] | None:
    selected = _output_for(
        output_paths,
        _VISUALIZATION_OUTPUTS.get(str(record.get("recipe")), ()),
    )
    if selected is None or not selected[1].is_file():
        return None
    return {
        "target_type": "visualization_set",
        "garden_id": manifest.garden_id,
        "domain": "visualize",
        "identifier": slugify_name(f"{record.get('run_id')}_compliance_visualization"),
        "path": to_posix_relative(selected[1], garden_root),
    }


def read_daylight_compliance(
    *,
    garden_root: str,
    run_target: dict[str, Any],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """Read a compact summary from one completed daylight compliance run."""
    if page < 1:
        raise ValueError("page must be one or greater.")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if not isinstance(run_target, dict):
        raise ValueError("run_target must be a radiance_run target.")
    if run_target.get("garden_id") != manifest.garden_id:
        raise ValueError("run_target belongs to a different Garden.")
    record = _run_record(garden_root_path, run_target=run_target, run_id=None)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    recipe = str(record.get("recipe") or "")
    if recipe not in COMPLIANCE_RECIPES:
        allowed = ", ".join(sorted(COMPLIANCE_RECIPES))
        raise ValueError(
            f"RAD_read_daylight_compliance only supports completed compliance recipes: {allowed}."
        )

    warnings: list[str] = []
    output_entries, output_paths = _output_entries(garden_root_path, record)
    overview = _overview(recipe, output_paths, warnings)
    spaces = _space_page(
        recipe,
        output_paths,
        page=page,
        page_size=page_size,
        warnings=warnings,
    )
    visualization_target = _visualization_target(
        garden_root_path,
        manifest,
        record,
        output_paths,
    )
    output_paths_view = {
        item["name"]: item["path"]
        for item in output_entries
        if item.get("path") is not None
    }
    target = record.get("target")
    summary_view = {
        "garden_target": manifest.target(),
        "run_target": target,
        "run_id": record.get("run_id"),
        "recipe": recipe,
        "status": record.get("status"),
        "space_summary": {
            key: spaces[key]
            for key in ("page", "page_size", "total", "page_count", "has_next")
        },
        "output_count": len(output_entries),
        "visualization_available": visualization_target is not None,
        "body_returned": False,
    }
    result: dict[str, Any] = {
        "target": target,
        "radiance_run_target": target,
        "run_target": target,
        "run_id": record.get("run_id"),
        "recipe": recipe,
        "compliance_summary": overview,
        "space_summary": spaces,
        "outputs": output_entries,
        "output_paths": output_paths_view,
        "visualization_set_target": visualization_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok" if overview is not None or spaces["items"] else "warning",
            message="Daylight compliance summary returned.",
            warnings=warnings,
        ),
    }
    return result
