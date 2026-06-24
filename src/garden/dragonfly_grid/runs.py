"""Garden-managed Dragonfly Electric Grid run ledgers."""

from __future__ import annotations

import json
import shutil
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

from dragonfly_energy.run import run_reopt as sdk_run_reopt
from dragonfly_energy.run import run_rnm as sdk_run_rnm

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.report import make_report

GRID_RUN_TARGET_TYPE = "dragonfly_grid_run"
GRID_RUN_DOMAIN = "dragonfly_grid"
GRID_RUN_ROOT = Path("runs") / "dragonfly_grid"
GRID_RUN_RECIPES = {"rnm", "opendss", "reopt"}
CONFIG_NEXT_TOOL = "config_get_runtime_config"

_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dragonfly-grid")
_index_lock = threading.Lock()


def start_rnm(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    underground_ratio: float = 0.9,
    lv_only: bool = True,
    nodes_per_building: int = 1,
) -> dict[str, Any]:
    """Start or block an RNM post-processing run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    normalized_run_id = _normalize_run_id(run_id, "rnm")
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="rnm",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={
            "operation": "run_rnm",
            "underground_ratio": underground_ratio,
            "lv_only": lv_only,
            "nodes_per_building": nodes_per_building,
        },
        preflight=_preflight_rnm_runtime(),
    )
    if record["status"] == "running":
        _BACKGROUND_EXECUTOR.submit(
            _run_rnm_job,
            garden_root=str(root),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            underground_ratio=underground_ratio,
            lv_only=lv_only,
            nodes_per_building=nodes_per_building,
        )
    latest = _run_record_by_id(root, "rnm", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def start_opendss(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    autosize: bool = False,
) -> dict[str, Any]:
    """Start or block an OpenDSS simulation run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    normalized_run_id = _normalize_run_id(run_id, "opendss")
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="opendss",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={"operation": "run_opendss", "autosize": autosize},
        preflight=_preflight_opendss_runtime(),
    )
    if record["status"] == "running":
        _complete_with_error(root, "opendss", normalized_run_id, "OpenDSS execution is not implemented in the MCP service yet.")
    latest = _run_record_by_id(root, "opendss", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def start_reopt(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    urdb_label: str,
    run_id: str | None = None,
    developer_key: str | None = None,
) -> dict[str, Any]:
    """Start or block a REopt post-processing run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    normalized_run_id = _normalize_run_id(run_id, "reopt")
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="reopt",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={"operation": "run_reopt", "urdb_label": urdb_label},
        preflight=_preflight_reopt_runtime(),
    )
    if record["status"] == "running":
        _BACKGROUND_EXECUTOR.submit(
            _run_reopt_job,
            garden_root=str(root),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            urdb_label=urdb_label,
            developer_key=developer_key,
        )
    latest = _run_record_by_id(root, "reopt", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _resolve_artifact(root: Path, manifest: GardenManifest, target: dict[str, Any], *, suffix: str) -> Path:
    if not isinstance(target, dict):
        raise ValueError("artifact target must be a dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("target must have target_type 'artifact'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("artifact target belongs to a different Garden.")
    path = target.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("artifact target requires a Garden-relative path.")
    resolved = (root / path).resolve()
    resolved.relative_to(root.resolve())
    if suffix and resolved.suffix.lower() != suffix:
        raise ValueError(f"artifact path must end with {suffix}.")
    if not resolved.exists():
        raise ValueError(f"artifact target file was not found: {path}")
    return resolved


def _preflight_rnm_runtime() -> dict[str, Any]:
    if shutil.which("uo"):
        return {"status": "ok", "runtime_status": "ready", "issues": []}
    return _blocked_preflight("rnm", "URBANopt/RNM runtime is not available.")


def _preflight_opendss_runtime() -> dict[str, Any]:
    if shutil.which("opendsscmd") or shutil.which("OpenDSSCmd"):
        return {"status": "ok", "runtime_status": "ready", "issues": []}
    return _blocked_preflight("opendss", "OpenDSS command runtime is not available.")


def _preflight_reopt_runtime() -> dict[str, Any]:
    if shutil.which("uo"):
        return {"status": "ok", "runtime_status": "ready", "issues": []}
    return _blocked_preflight("reopt", "URBANopt/REopt runtime is not available.")


def _blocked_preflight(name: str, message: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": [message],
        "missing": [name],
        "recommended_next_tools": [CONFIG_NEXT_TOOL],
    }


def _normalize_run_id(run_id: str | None, prefix: str) -> str:
    return slugify_name(run_id or f"{prefix}_{uuid4().hex[:8]}")


def _run_target(garden_id: str, run_id: str, recipe: str) -> dict[str, Any]:
    if recipe not in GRID_RUN_RECIPES:
        raise ValueError(f"Unsupported Dragonfly Grid recipe: {recipe}.")
    return {
        "target_type": GRID_RUN_TARGET_TYPE,
        "domain": GRID_RUN_DOMAIN,
        "garden_id": garden_id,
        "recipe": recipe,
        "run_id": run_id,
    }


def _run_dir(root: Path, recipe: str, run_id: str) -> Path:
    return root / GRID_RUN_ROOT / recipe / run_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _start_record(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    recipe: str,
    run_id: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    request: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    target = _run_target(manifest.garden_id, run_id, recipe)
    run_dir = _run_dir(garden_root, recipe, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "background_request.json",
        {
            **request,
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
        },
    )
    status = "blocked" if preflight.get("runtime_status") == "blocked" else "running"
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": recipe,
        "status": status,
        "runtime_status": status,
        "created_at": utc_now_iso(),
        "started_at": None if status == "blocked" else utc_now_iso(),
        "completed_at": utc_now_iso() if status == "blocked" else None,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "preflight": preflight,
        "outputs": [],
        "error": "; ".join(preflight.get("issues", [])) if status == "blocked" else None,
    }
    _upsert_record(garden_root, recipe, record)
    return record


def _index_path(root: Path, recipe: str) -> Path:
    return root / GRID_RUN_ROOT / recipe / "index.json"


def _read_index(root: Path, recipe: str) -> dict[str, Any]:
    path = _index_path(root, recipe)
    if not path.is_file():
        return {"runs": []}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _upsert_record(root: Path, recipe: str, record: dict[str, Any]) -> None:
    with _index_lock:
        index = _read_index(root, recipe)
        index["runs"] = [
            existing
            for existing in index.get("runs", [])
            if existing.get("run_id") != record["run_id"]
        ]
        index["runs"].append(record)
        _write_json(_index_path(root, recipe), index)


def _run_record_by_id(root: Path, recipe: str, run_id: str) -> dict[str, Any] | None:
    for record in _read_index(root, recipe).get("runs", []):
        if record.get("run_id") == run_id:
            return record
    return None


def _complete_with_error(root: Path, recipe: str, run_id: str, message: str) -> None:
    record = _run_record_by_id(root, recipe, run_id)
    if record is None:
        return
    record.update(
        {
            "status": "failed",
            "runtime_status": "failed",
            "completed_at": utc_now_iso(),
            "error": message,
        }
    )
    _upsert_record(root, recipe, record)


def _run_rnm_job(**kwargs: Any) -> None:
    root = Path(kwargs["garden_root"])
    run_id = kwargs["run_id"]
    try:
        sdk_run_rnm(
            kwargs["feature_geojson"],
            kwargs["scenario_csv"],
            underground_ratio=kwargs["underground_ratio"],
            lv_only=kwargs["lv_only"],
            nodes_per_building=kwargs["nodes_per_building"],
        )
        _complete_success(root, "rnm", run_id)
    except Exception:  # pragma: no cover - external runtime diagnostics vary
        _complete_with_error(root, "rnm", run_id, traceback.format_exc())


def _run_reopt_job(**kwargs: Any) -> None:
    root = Path(kwargs["garden_root"])
    run_id = kwargs["run_id"]
    try:
        sdk_run_reopt(
            kwargs["feature_geojson"],
            kwargs["scenario_csv"],
            kwargs["urdb_label"],
            developer_key=kwargs["developer_key"],
        )
        _complete_success(root, "reopt", run_id)
    except Exception:  # pragma: no cover - external runtime diagnostics vary
        _complete_with_error(root, "reopt", run_id, traceback.format_exc())


def _complete_success(root: Path, recipe: str, run_id: str) -> None:
    record = _run_record_by_id(root, recipe, run_id)
    if record is None:
        return
    record.update(
        {
            "status": "completed",
            "runtime_status": "completed",
            "completed_at": utc_now_iso(),
            "outputs": _scan_outputs(root / record["run_folder"]),
            "error": None,
        }
    )
    _upsert_record(root, recipe, record)


def _scan_outputs(run_dir: Path) -> list[dict[str, Any]]:
    if not run_dir.exists():
        return []
    outputs = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        outputs.append(
            {
                "name": path.name,
                "path": to_posix_relative(path, run_dir.parents[2]),
                "exists": True,
                "kind": path.suffix.lower().lstrip(".") or "file",
            }
        )
    return outputs


def _result_from_record(root: Path, manifest: GardenManifest, record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("runtime_status") or record.get("status") or "unknown")
    recommended = list(
        record.get("preflight", {}).get("recommended_next_tools")
        or ([CONFIG_NEXT_TOOL] if status == "blocked" else [])
    )
    poll_next = {
        "tool": f"df_grid_start_{record['recipe']}" if status == "blocked" else None,
        "run_target": record["target"],
        "run_id": record["run_id"],
    }
    return {
        "target": record["target"],
        "run_target": record["target"],
        "runtime_status": status,
        "poll_next": poll_next,
        "summary_view": {
            "garden_target": manifest.target(),
            "run": {
                "run_id": record["run_id"],
                "recipe": record["recipe"],
                "status": record.get("status"),
                "runtime_status": status,
            },
            "recommended_next_tools": recommended,
            "output_count": len(record.get("outputs", [])),
        },
        "report": make_report(
            status=status if status in {"blocked", "failed"} else "ok",
            message=f"Dragonfly Grid {record['recipe']} run {status}: {record['run_id']}",
            details={
                "run_target": record["target"],
                "error": record.get("error"),
                "recommended_next_tools": recommended,
            },
        ),
    }

