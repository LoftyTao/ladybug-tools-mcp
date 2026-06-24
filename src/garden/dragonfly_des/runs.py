"""Garden-managed Dragonfly DES run ledgers and runtime-gated commands."""

from __future__ import annotations

import json
import shutil
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_des_modelica as sdk_run_des_modelica
from dragonfly_energy.run import run_des_sys_param as sdk_run_des_sys_param
from dragonfly_energy.run import run_modelica_docker as sdk_run_modelica_docker
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt
from dragonfly_energy.run import set_building_district_loads as sdk_set_building_district_loads
from honeybee.config import folders as hb_folders

from garden.ladybug_tools_config import get_ladybug_tools_config
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

from .artifacts import (
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_MODELICA_PROJECT_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE,
    artifact_target_for_path,
    register_des_artifacts,
    resolve_des_artifact_path,
)

DES_RUN_TARGET_TYPE = "dragonfly_des_run"
DES_RUN_DOMAIN = "dragonfly_des"
DES_RUN_ROOT = Path("runs") / "dragonfly_des"
DES_RUN_RECIPES = {"urbanopt", "sys_param", "modelica"}
CONFIG_NEXT_TOOL = "config_get_runtime_config"

_index_lock = threading.Lock()


def prepare_urbanopt_project(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    cpu_count: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Prepare a Garden URBANopt project folder from a feature GeoJSON artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    preflight = _preflight_urbanopt_runtime()
    if preflight["runtime_status"] == "blocked":
        return _operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="prepare_urbanopt_project",
            preflight=preflight,
        )

    scenario_csv = Path(
        sdk_prepare_urbanopt_folder(
            str(feature_geojson),
            cpu_count=cpu_count,
            verbose=verbose,
        )
    ).expanduser().resolve()
    scenario_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(feature_geojson.stem)}_prepared_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=_bounded_existing_path(garden_root_path, scenario_csv, suffix=".csv"),
    )
    register_des_artifacts(
        manifest=manifest,
        garden_root=garden_root_path,
        targets=[scenario_target],
    )
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        artifact_path=scenario_target["path"],
        absolute_path=str(scenario_csv),
        source={"feature_geojson_target": feature_geojson_target},
    )
    return {
        "target": scenario_target,
        "scenario_csv_target": scenario_target,
        "runtime_status": "ready",
        "summary_view": {
            "garden_target": manifest.target(),
            "prepared": True,
            "runtime_status": "ready",
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_target,
            "preflight": preflight,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message="Prepared URBANopt project folder.",
        ),
    }


def start_urbanopt_simulation(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    cpu_count: int | None = None,
) -> dict[str, Any]:
    """Start an URBANopt run after runtime preflight and write a DES run ledger."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _normalize_run_id(run_id, "urbanopt")
    target = _run_target(manifest.garden_id, normalized_run_id, "urbanopt")
    run_dir = garden_root_path / DES_RUN_ROOT / "urbanopt" / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    request = {
        "operation": "run_urbanopt",
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "cpu_count": cpu_count,
    }
    _write_background_request(run_dir, request)
    preflight = _preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        recipe="urbanopt",
        status=status,
        run_dir=run_dir,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
    )
    _upsert_record(garden_root_path, "urbanopt", record)
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_urbanopt_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            cpu_count=cpu_count,
        )
    latest = _run_record_by_id(garden_root_path, "urbanopt", normalized_run_id) or record
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"URBANopt run {latest['runtime_status']}: {normalized_run_id}",
    )


def poll_urbanopt_simulation(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one URBANopt run ledger record."""
    return _poll_run(garden_root=garden_root, recipe="urbanopt", run_target=run_target, run_id=run_id)


def list_urbanopt_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List output files for one URBANopt run ledger record."""
    return _list_run_outputs(
        garden_root=garden_root,
        recipe="urbanopt",
        run_target=run_target,
        run_id=run_id,
    )


def assign_building_loads(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
) -> dict[str, Any]:
    """Assign building loads for DES simulation using SDK output files."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    preflight = _preflight_gmt_runtime()
    if preflight["runtime_status"] == "blocked":
        return _operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="assign_building_loads",
            preflight=preflight,
        )
    warnings = sdk_set_building_district_loads(str(feature_geojson), str(scenario_csv))
    return {
        "runtime_status": "completed",
        "summary_view": {
            "garden_target": manifest.target(),
            "runtime_status": "completed",
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
            "warning_count": len(warnings),
            "preflight": preflight,
        },
        "report": make_report(
            status="ok",
            message="Assigned building district loads for DES.",
            warnings=list(warnings),
        ),
    }


def start_sys_param(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    system_parameter_json_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Start a DES system-parameter update run after GMT preflight."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    if system_parameter_json_target is not None:
        _resolve_system_parameter_json(
            garden_root_path,
            manifest,
            system_parameter_json_target,
        )
    normalized_run_id = _normalize_run_id(run_id, "sys_param")
    target = _run_target(manifest.garden_id, normalized_run_id, "sys_param")
    run_dir = garden_root_path / DES_RUN_ROOT / "sys_param" / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_background_request(
        run_dir,
        {
            "operation": "run_des_sys_param",
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
            "system_parameter_json_target": system_parameter_json_target or {},
        },
    )
    preflight = _preflight_gmt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        recipe="sys_param",
        status=status,
        run_dir=run_dir,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        system_parameter_json_target=system_parameter_json_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
    )
    _upsert_record(garden_root_path, "sys_param", record)
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_sys_param_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            system_parameter_json_target=system_parameter_json_target,
        )
    latest = _run_record_by_id(garden_root_path, "sys_param", normalized_run_id) or record
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"DES system-parameter run {latest['runtime_status']}: {normalized_run_id}",
    )


def poll_sys_param(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one DES system-parameter run ledger record."""
    return _poll_run(garden_root=garden_root, recipe="sys_param", run_target=run_target, run_id=run_id)


def write_modelica_project(
    *,
    garden_root: str,
    system_parameter_json_target: dict[str, Any],
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    """Candidate: write a Modelica project from DES system-parameter artifacts."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    system_parameter = _resolve_system_parameter_json(
        garden_root_path,
        manifest,
        system_parameter_json_target,
    )
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _normalize_run_id(run_id, "modelica")
    target = _run_target(manifest.garden_id, normalized_run_id, "modelica")
    run_dir = garden_root_path / DES_RUN_ROOT / "modelica" / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_background_request(
        run_dir,
        {
            "operation": "run_des_modelica",
            "system_parameter_json_target": system_parameter_json_target,
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
            "candidate_status": "candidate",
        },
    )
    preflight = _preflight_gmt_runtime()
    if preflight["runtime_status"] == "blocked":
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            recipe="modelica",
            status="blocked",
            run_dir=run_dir,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            preflight=preflight,
            completed_at=utc_now_iso(),
            error="; ".join(preflight["issues"]),
            candidate_status="candidate",
        )
        _upsert_record(garden_root_path, "modelica", record)
        return _result_from_record(
            garden_root=garden_root_path,
            manifest=manifest,
            record=record,
            message=f"Modelica project write blocked: {normalized_run_id}",
        )

    try:
        project_dir_value = sdk_run_des_modelica(
            str(system_parameter),
            str(feature_geojson),
            str(scenario_csv),
        )
        if project_dir_value is None:
            raise RuntimeError("The SDK did not write a Modelica project for this DES loop.")
        project_dir = _bounded_existing_directory(garden_root_path, project_dir_value)
        project_target = artifact_target_for_path(
            manifest=manifest,
            garden_root=garden_root_path,
            identifier=f"{normalized_run_id}_modelica_project",
            artifact_type=DES_MODELICA_PROJECT_ARTIFACT_TYPE,
            path=project_dir,
        )
        register_des_artifacts(
            manifest=manifest,
            garden_root=garden_root_path,
            targets=[project_target],
        )
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            recipe="modelica",
            status="completed",
            run_dir=run_dir,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            modelica_project_target=project_target,
            preflight=preflight,
            completed_at=utc_now_iso(),
            outputs=[_output_for_path(garden_root_path, project_dir, name="modelica_project")],
            candidate_status="candidate",
        )
    except Exception as exc:
        record = _failed_record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            recipe="modelica",
            run_dir=run_dir,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            preflight=preflight,
            error=str(exc),
            candidate_status="candidate",
        )
    _upsert_record(garden_root_path, "modelica", record)
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Modelica project write {record['runtime_status']}: {normalized_run_id}",
    )


def start_modelica_simulation(
    *,
    garden_root: str,
    modelica_project_target: dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    """Candidate: start a runtime-gated Modelica Docker simulation."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    project_dir = resolve_des_artifact_path(
        garden_root=garden_root_path,
        manifest=manifest,
        target=modelica_project_target,
        expected_artifact_type=DES_MODELICA_PROJECT_ARTIFACT_TYPE,
        expect_directory=True,
    )
    normalized_run_id = _normalize_run_id(run_id, "modelica")
    target = _run_target(manifest.garden_id, normalized_run_id, "modelica")
    run_dir = garden_root_path / DES_RUN_ROOT / "modelica" / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_background_request(
        run_dir,
        {
            "operation": "run_modelica_docker",
            "modelica_project_target": modelica_project_target,
            "candidate_status": "candidate",
        },
    )
    preflight = _preflight_modelica_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        recipe="modelica",
        status=status,
        run_dir=run_dir,
        modelica_project_target=modelica_project_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
        candidate_status="candidate",
    )
    _upsert_record(garden_root_path, "modelica", record)
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_modelica_simulation_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            modelica_project_dir=str(project_dir),
        )
    latest = _run_record_by_id(garden_root_path, "modelica", normalized_run_id) or record
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"Modelica simulation {latest['runtime_status']}: {normalized_run_id}",
    )


def poll_modelica_simulation(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one candidate Modelica run ledger record without numeric result parsing."""
    return _poll_run(garden_root=garden_root, recipe="modelica", run_target=run_target, run_id=run_id)


def _poll_run(
    *,
    garden_root: str,
    recipe: str,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id, recipe=recipe)
    record = _run_record_by_id(garden_root_path, recipe, resolved_id)
    if record is None:
        raise ValueError(f"Dragonfly DES {recipe} run not found: {resolved_id}")
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Dragonfly DES {recipe} run returned: {resolved_id}",
    )


def _list_run_outputs(
    *,
    garden_root: str,
    recipe: str,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id, recipe=recipe)
    record = _run_record_by_id(garden_root_path, recipe, resolved_id)
    if record is None:
        raise ValueError(f"Dragonfly DES {recipe} run not found: {resolved_id}")
    outputs = list(record.get("outputs") or [])
    if not outputs:
        run_folder = record.get("run_folder")
        if isinstance(run_folder, str):
            outputs = _discover_outputs(garden_root_path, garden_root_path / run_folder)
    return {
        "matches": outputs,
        "outputs": outputs,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_id,
            "recipe": recipe,
            "count": len(outputs),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(outputs)} output(s) for Dragonfly DES {recipe} run {resolved_id}.",
        ),
    }


def _run_urbanopt_job(
    *,
    garden_root: str,
    run_id: str,
    feature_geojson: str,
    scenario_csv: str,
    cpu_count: int | None,
) -> None:
    garden_root_path = _garden_root(garden_root)
    record = _run_record_by_id(garden_root_path, "urbanopt", run_id)
    if record is None:
        return
    try:
        outputs = sdk_run_urbanopt(feature_geojson, scenario_csv, cpu_count=cpu_count)
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": _outputs_from_sdk_result(garden_root_path, outputs),
            }
        )
    except Exception as exc:
        record.update(_failure_fields(str(exc), traceback.format_exc()))
    _upsert_record(garden_root_path, "urbanopt", record)


def _run_sys_param_job(
    *,
    garden_root: str,
    run_id: str,
    feature_geojson: str,
    scenario_csv: str,
    system_parameter_json_target: dict[str, Any] | None,
) -> None:
    garden_root_path = _garden_root(garden_root)
    record = _run_record_by_id(garden_root_path, "sys_param", run_id)
    if record is None:
        return
    try:
        sys_param_path = Path(sdk_run_des_sys_param(feature_geojson, scenario_csv)).resolve()
        outputs = [_output_for_path(garden_root_path, sys_param_path, name="system_params")]
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": outputs,
                "system_parameter_json_target": system_parameter_json_target or record.get(
                    "system_parameter_json_target", {}
                ),
            }
        )
    except Exception as exc:
        record.update(_failure_fields(str(exc), traceback.format_exc()))
    _upsert_record(garden_root_path, "sys_param", record)


def _run_modelica_simulation_job(
    *,
    garden_root: str,
    run_id: str,
    modelica_project_dir: str,
) -> None:
    garden_root_path = _garden_root(garden_root)
    record = _run_record_by_id(garden_root_path, "modelica", run_id)
    if record is None:
        return
    try:
        result_dir = _bounded_existing_directory(
            garden_root_path,
            sdk_run_modelica_docker(modelica_project_dir),
        )
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": [_output_for_path(garden_root_path, result_dir, name="modelica_results")],
            }
        )
    except Exception as exc:
        record.update(_failure_fields(str(exc), traceback.format_exc()))
    _upsert_record(garden_root_path, "modelica", record)


class _BackgroundExecutor:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="des")

    def submit(self, fn, **kwargs):
        return self._executor.submit(fn, **kwargs)


_BACKGROUND_EXECUTOR = _BackgroundExecutor()


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _resolve_feature_geojson(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        suffix=".geojson",
    )


def _resolve_scenario_csv(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        suffix=".csv",
    )


def _resolve_system_parameter_json(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE,
        suffix=".json",
    )


def _bounded_existing_path(garden_root: Path, value: str | Path, *, suffix: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("Dragonfly DES runtime artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} artifact: {path}")
    if not path.is_file():
        raise ValueError(f"Dragonfly DES artifact not found: {path}")
    return path


def _bounded_existing_directory(garden_root: Path, value: str | Path | None) -> Path:
    if value is None:
        raise ValueError("Expected a Modelica project directory path.")
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("Dragonfly DES project directories must stay inside the Garden.") from exc
    if not path.is_dir():
        raise ValueError(f"Dragonfly DES project directory not found: {path}")
    return path


def _preflight_urbanopt_runtime() -> dict[str, Any]:
    config = get_ladybug_tools_config()
    urbanopt = config["summary_view"]["engines"].get("urbanopt", {})
    issues = []
    if not urbanopt.get("available"):
        issues.append("URBANopt CLI or Gemfile is not available to dragonfly_energy.")
    if urbanopt.get("version_status") in {"older", "newer", "unknown"}:
        issues.append("URBANopt runtime version does not match the current DEV requirement.")
    if issues:
        return _blocked_preflight(issues, missing=["urbanopt"], runtime=urbanopt)
    return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": urbanopt}


def _preflight_gmt_runtime() -> dict[str, Any]:
    scripts_path = Path(str(hb_folders.python_scripts_path or "")).expanduser()
    exe_name = "uo_des.exe" if _is_windows() else "uo_des"
    gmt_exe = scripts_path / exe_name
    if not gmt_exe.is_file():
        return _blocked_preflight(
            [f"GMT / uo_des command was not found at {gmt_exe}."],
            missing=["gmt"],
            runtime={"python_scripts_path": str(scripts_path), "expected_exe": str(gmt_exe)},
        )
    return {
        "status": "ok",
        "runtime_status": "ready",
        "issues": [],
        "runtime": {"python_scripts_path": str(scripts_path), "gmt_exe": str(gmt_exe)},
    }


def _preflight_modelica_runtime() -> dict[str, Any]:
    gmt = _preflight_gmt_runtime()
    issues = list(gmt.get("issues") or [])
    missing = list(gmt.get("missing") or [])
    docker = shutil.which("docker")
    omc = shutil.which("omc")
    if docker is None:
        issues.append("Docker command is not available on PATH.")
        missing.append("docker")
    if omc is None:
        issues.append("OpenModelica omc command is not available on PATH.")
        missing.append("openmodelica")
    if issues:
        return _blocked_preflight(
            issues,
            missing=missing,
            runtime={"gmt": gmt.get("runtime"), "docker": docker, "omc": omc},
        )
    return {
        "status": "ok",
        "runtime_status": "ready",
        "issues": [],
        "runtime": {"gmt": gmt.get("runtime"), "docker": docker, "omc": omc},
    }


def _blocked_preflight(
    issues: list[str],
    *,
    missing: list[str],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": issues,
        "missing": sorted(set(missing)),
        "runtime": runtime,
        "recommended_next_tools": [CONFIG_NEXT_TOOL],
    }


def _operation_blocked_result(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    operation: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    recommended = list(preflight.get("recommended_next_tools") or [CONFIG_NEXT_TOOL])
    return {
        "runtime_status": "blocked",
        "summary_view": {
            "garden_target": manifest.target(),
            "operation": operation,
            "runtime_status": "blocked",
            "preflight": preflight,
            "recommended_next_tools": recommended,
        },
        "report": make_report(
            status="warning",
            message=f"Dragonfly DES operation blocked by missing runtime: {operation}",
            warnings=list(preflight.get("issues") or []),
            details={
                "garden_root": str(garden_root),
                "recommended_next_tools": recommended,
                "preflight": preflight,
            },
        ),
    }


def _is_windows() -> bool:
    import os

    return os.name == "nt"


def _normalize_run_id(value: str | None, recipe: str) -> str:
    if value:
        return slugify_name(value)
    return slugify_name(f"des_{recipe}_{utc_now_iso()}_{uuid4().hex[:8]}")


def _run_target(garden_id: str, run_id: str, recipe: str) -> dict[str, Any]:
    if recipe not in DES_RUN_RECIPES:
        raise ValueError(f"Unsupported Dragonfly DES run recipe: {recipe}.")
    return {
        "target_type": DES_RUN_TARGET_TYPE,
        "domain": DES_RUN_DOMAIN,
        "garden_id": garden_id,
        "recipe": recipe,
        "run_id": run_id,
    }


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
    recipe: str,
) -> str:
    if run_target is not None:
        if run_target.get("target_type") != DES_RUN_TARGET_TYPE:
            raise ValueError("run_target must be a dragonfly_des_run target.")
        if run_target.get("domain") != DES_RUN_DOMAIN:
            raise ValueError("run_target must reference domain 'dragonfly_des'.")
        if run_target.get("recipe") != recipe:
            raise ValueError(f"run_target must reference recipe '{recipe}'.")
        value = run_target.get("run_id")
        if not value:
            raise ValueError("run_target requires run_id.")
        return str(value)
    if run_id:
        return slugify_name(run_id)
    raise ValueError("Pass run_target or run_id.")


def _record(
    *,
    garden_root: Path,
    run_id: str,
    target: dict[str, Any],
    recipe: str,
    status: str,
    run_dir: Path,
    preflight: dict[str, Any],
    completed_at: str | None = None,
    error: str | None = None,
    outputs: list[dict[str, Any]] | None = None,
    candidate_status: str | None = None,
    **targets: Any,
) -> dict[str, Any]:
    started_at = utc_now_iso()
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": recipe,
        "status": status,
        "runtime_status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "preflight": preflight,
        "outputs": outputs or [],
    }
    for key, value in targets.items():
        if value is not None:
            record[key] = value
    if candidate_status is not None:
        record["candidate_status"] = candidate_status
    if completed_at is not None:
        record["completed_at"] = completed_at
    if error:
        record["error"] = error
    return record


def _failed_record(
    *,
    garden_root: Path,
    run_id: str,
    target: dict[str, Any],
    recipe: str,
    run_dir: Path,
    preflight: dict[str, Any],
    error: str,
    candidate_status: str | None = None,
    **targets: Any,
) -> dict[str, Any]:
    record = _record(
        garden_root=garden_root,
        run_id=run_id,
        target=target,
        recipe=recipe,
        status="failed",
        run_dir=run_dir,
        preflight=preflight,
        completed_at=utc_now_iso(),
        error=error,
        candidate_status=candidate_status,
        **targets,
    )
    return record


def _failure_fields(error: str, traceback_text: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "runtime_status": "failed",
        "completed_at": utc_now_iso(),
        "error": error,
        "traceback": traceback_text,
    }


def _write_background_request(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "background_request.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _index_path(garden_root: Path, recipe: str) -> Path:
    return garden_root / DES_RUN_ROOT / recipe / "index.json"


def _read_index(garden_root: Path, recipe: str) -> list[dict[str, Any]]:
    path = _index_path(garden_root, recipe)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return list(json.loads(text).get("runs", []))


def _write_index(garden_root: Path, recipe: str, records: list[dict[str, Any]]) -> None:
    path = _index_path(garden_root, recipe)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"runs": records}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _upsert_record(garden_root: Path, recipe: str, record: dict[str, Any]) -> None:
    with _index_lock:
        records = [
            item for item in _read_index(garden_root, recipe) if item.get("run_id") != record["run_id"]
        ]
        records.append(record)
        _write_index(garden_root, recipe, records)


def _run_record_by_id(garden_root: Path, recipe: str, run_id: str) -> dict[str, Any] | None:
    for record in _read_index(garden_root, recipe):
        if record.get("run_id") == run_id:
            return record
    return None


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "target",
        "recipe",
        "status",
        "runtime_status",
        "candidate_status",
        "created_at",
        "started_at",
        "completed_at",
        "run_folder",
        "feature_geojson_target",
        "scenario_csv_target",
        "system_parameter_json_target",
        "modelica_project_target",
        "preflight",
        "outputs",
        "error",
    )
    return {key: record.get(key) for key in keys if key in record}


def _result_from_record(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    target = record["target"]
    runtime_status = record["runtime_status"]
    recommended = list((record.get("preflight") or {}).get("recommended_next_tools") or [])
    if runtime_status in {"blocked", "failed"} and not recommended:
        recommended = [CONFIG_NEXT_TOOL]
    poll_next = {
        "tool": _poll_tool_name(record["recipe"]),
        "arguments": {"garden_root": str(garden_root), "run_target": target},
    }
    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "recipe": record["recipe"],
        "status": runtime_status,
        "runtime_status": runtime_status,
        "run": _public_run(record),
        "outputs": record.get("outputs") or [],
        "poll_next": poll_next,
        "preflight": record.get("preflight"),
        "recommended_next_tools": recommended,
    }
    if record.get("candidate_status"):
        summary_view["candidate_status"] = record["candidate_status"]
    report_status = "warning" if runtime_status in {"blocked", "failed"} else "ok"
    result = {
        "target": target,
        "run_target": target,
        "runtime_status": runtime_status,
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status=report_status,
            message=message,
            warnings=list((record.get("preflight") or {}).get("issues") or []),
            details={
                "recommended_next_tools": recommended,
                "preflight": record.get("preflight"),
            },
        ),
    }
    for key in ("system_parameter_json_target", "modelica_project_target"):
        if key in record:
            result[key] = record[key]
    return result


def _poll_tool_name(recipe: str) -> str:
    return {
        "urbanopt": "des_poll_urbanopt_simulation",
        "sys_param": "des_poll_sys_param",
        "modelica": "des_poll_modelica_simulation",
    }[recipe]


def _output_for_path(garden_root: Path, path: Path, *, name: str | None = None) -> dict[str, Any]:
    return {
        "name": name or path.name,
        "path": to_posix_relative(path, garden_root),
        "exists": path.exists(),
        "is_directory": path.is_dir(),
    }


def _outputs_from_sdk_result(garden_root: Path, value: Any) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for output_type, paths in value.items():
            if isinstance(paths, (list, tuple)):
                for path in paths:
                    outputs.append(
                        _output_for_path(garden_root, Path(path).resolve(), name=f"{output_type}:{Path(path).name}")
                    )
            elif paths:
                outputs.append(
                    _output_for_path(garden_root, Path(paths).resolve(), name=str(output_type))
                )
    elif isinstance(value, (list, tuple)):
        for path in value:
            outputs.append(_output_for_path(garden_root, Path(path).resolve()))
    elif value:
        outputs.append(_output_for_path(garden_root, Path(value).resolve()))
    return outputs


def _discover_outputs(garden_root: Path, run_dir: Path) -> list[dict[str, Any]]:
    if not run_dir.is_dir():
        return []
    outputs = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name == "background_request.json":
            continue
        outputs.append(_output_for_path(garden_root, path))
    return outputs
