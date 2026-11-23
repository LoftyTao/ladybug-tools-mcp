"""Garden-managed Dragonfly DES run ledgers and runtime-gated commands."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import traceback
from typing import Any

from dragonfly_energy.run import base_honeybee_osw as sdk_base_honeybee_osw
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_des_modelica as sdk_run_des_modelica
from dragonfly_energy.run import run_des_sys_param as sdk_run_des_sys_param
from dragonfly_energy.run import run_modelica_docker as sdk_run_modelica_docker
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt
from dragonfly_energy.run import set_building_district_loads as sdk_set_building_district_loads
from honeybee.config import folders as hb_folders

from garden.ladybug_tools_config import (
    get_ladybug_tools_config,
    urbanopt_runtime_env,
    write_urbanopt_bundle_config,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_energy.config import resolve_garden_weather_epw
from garden.run_ledger import RunLedger, RunManager
from garden.urbanopt_cli import (
    CONFIG_NEXT_TOOL,
    DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY,
    attach_runtime_diagnostics,
    blocked_preflight,
    discover_urbanopt_outputs,
    failed_urbanopt_job_error,
    has_urbanopt_cli_bundle,
    operation_blocked_result,
    output_for_path,
    outputs_from_sdk_result,
    preflight_urbanopt_runtime,
    run_urbanopt_energy_with_cli_bundle,
)
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

from .export import (
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
DEFAULT_DES_NETWORK_POLICY = DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY
STALE_RUNNING_SECONDS = 60 * 60

_DES_RUNS = RunManager(
    domain=DES_RUN_DOMAIN,
    target_type=DES_RUN_TARGET_TYPE,
    runs_dir=DES_RUN_ROOT,
    default_recipe="urbanopt",
    allowed_recipes=DES_RUN_RECIPES,
    per_recipe_index=True,
    run_id_prefix="des",
    use_uuid_fallback=True,
    slug_lookup=True,
    domain_message="run_target must reference domain 'dragonfly_des'.",
    missing_message="Pass run_target or run_id.",
    not_found_label="Dragonfly DES",
    public_fields=(
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
    ),
    ledger=RunLedger(lock="thread", empty_is_empty=True),
)
_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="des")


def prepare_urbanopt_project(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    weather_target: dict[str, Any] | None = None,
    cpu_count: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Prepare a Garden URBANopt project folder from a feature GeoJSON artifact."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    epw_path = (
        resolve_garden_weather_epw(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        if weather_target is not None
        else None
    )
    preflight = preflight_urbanopt_runtime()
    if preflight["runtime_status"] == "blocked":
        return operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="prepare_urbanopt_project",
            preflight=preflight,
            label="Dragonfly DES",
        )

    runtime = preflight.get("runtime")
    sdk_base_honeybee_osw(
        str(feature_geojson.parent),
        epw_file=str(epw_path) if epw_path is not None else None,
        skip_report=False,
    )
    write_urbanopt_bundle_config(feature_geojson.parent, runtime)
    scenario_csv = Path(
        sdk_prepare_urbanopt_folder(
            str(feature_geojson),
            cpu_count=cpu_count,
            verbose=verbose,
        )
    ).expanduser().resolve()
    write_urbanopt_bundle_config(feature_geojson.parent, runtime)
    scenario_csv = resolve_existing_garden_path(
        garden_root_path, scenario_csv, kind="file", suffix=".csv", label="Dragonfly DES runtime artifact"
    )
    scenario_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(feature_geojson.stem)}_prepared_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=scenario_csv,
    )
    register_des_artifacts(manifest=manifest, garden_root=garden_root_path, targets=[scenario_target])
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        artifact_path=scenario_target["path"],
        absolute_path=str(scenario_csv),
        source={"feature_geojson_target": feature_geojson_target},
    )
    summary_view = {
        "garden_target": manifest.target(),
        "prepared": True,
        "runtime_status": "ready",
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_target,
        "preflight": preflight,
    }
    if weather_target is not None:
        summary_view["weather_target"] = weather_target
    return {
        "target": scenario_target,
        "scenario_csv_target": scenario_target,
        "runtime_status": "ready",
        "summary_view": summary_view,
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message="Prepared URBANopt project folder."),
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _DES_RUNS.normalize_run_id(run_id, recipe="urbanopt")
    run_dir = _DES_RUNS.run_dir(garden_root_path, normalized_run_id, recipe="urbanopt")
    _write_background_request(
        run_dir,
        {
            "operation": "run_urbanopt",
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
            "cpu_count": cpu_count,
        },
    )
    preflight = preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=_DES_RUNS.make_target(manifest.garden_id, normalized_run_id, recipe="urbanopt"),
        recipe="urbanopt",
        status=status,
        run_dir=run_dir,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
    )
    _DES_RUNS.upsert(garden_root_path, record, recipe="urbanopt")
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_urbanopt_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            cpu_count=cpu_count,
            runtime=preflight.get("runtime"),
        )
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="urbanopt") or record
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _DES_RUNS.resolve_run_id(run_target, run_id, recipe="urbanopt")
    record = _DES_RUNS.get(garden_root_path, resolved_id, recipe="urbanopt")
    if record is None:
        raise ValueError(f"Dragonfly DES urbanopt run not found: {resolved_id}")
    record = _stabilize_running_record(garden_root_path, "urbanopt", record)
    outputs = list(record.get("outputs") or [])
    if not outputs and isinstance(record.get("run_folder"), str):
        outputs = discover_urbanopt_outputs(
            garden_root_path, garden_root_path / record["run_folder"], include_kind=False
        )
    return {
        "matches": outputs,
        "outputs": outputs,
        "runtime_status": record.get("runtime_status"),
        "run_target": record.get("target"),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_id,
            "recipe": "urbanopt",
            "status": record.get("runtime_status"),
            "runtime_status": record.get("runtime_status"),
            "run": _DES_RUNS.public_run(record),
            "count": len(outputs),
        },
        "report": make_report(
            status="warning" if record.get("runtime_status") in {"blocked", "failed"} else "ok",
            message=f"Found {len(outputs)} output(s) for Dragonfly DES urbanopt run {resolved_id}.",
            warnings=[record["error"]] if record.get("error") else [],
        ),
    }


def assign_building_loads(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
) -> dict[str, Any]:
    """Assign building loads for DES simulation using SDK output files."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    preflight = _preflight_gmt_runtime()
    if preflight["runtime_status"] == "blocked":
        return operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="assign_building_loads",
            preflight=preflight,
            label="Dragonfly DES",
        )
    warnings = sdk_set_building_district_loads(str(scenario_csv))
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    if system_parameter_json_target is not None:
        _resolve_system_parameter_json(garden_root_path, manifest, system_parameter_json_target)
    normalized_run_id = _DES_RUNS.normalize_run_id(run_id, recipe="sys_param")
    run_dir = _DES_RUNS.run_dir(garden_root_path, normalized_run_id, recipe="sys_param")
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
        target=_DES_RUNS.make_target(manifest.garden_id, normalized_run_id, recipe="sys_param"),
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
    _DES_RUNS.upsert(garden_root_path, record, recipe="sys_param")
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_sys_param_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            system_parameter_json_target=system_parameter_json_target,
        )
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="sys_param") or record
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    system_parameter = _resolve_system_parameter_json(
        garden_root_path, manifest, system_parameter_json_target
    )
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _DES_RUNS.normalize_run_id(run_id, recipe="modelica")
    target = _DES_RUNS.make_target(manifest.garden_id, normalized_run_id, recipe="modelica")
    run_dir = _DES_RUNS.run_dir(garden_root_path, normalized_run_id, recipe="modelica")
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
        _DES_RUNS.upsert(garden_root_path, record, recipe="modelica")
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
        project_dir = resolve_existing_garden_path(
            garden_root_path, project_dir_value, kind="directory", label="Dragonfly DES project directory"
        )
        project_target = artifact_target_for_path(
            manifest=manifest,
            garden_root=garden_root_path,
            identifier=f"{normalized_run_id}_modelica_project",
            artifact_type=DES_MODELICA_PROJECT_ARTIFACT_TYPE,
            path=project_dir,
        )
        register_des_artifacts(manifest=manifest, garden_root=garden_root_path, targets=[project_target])
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
            outputs=[
                output_for_path(
                    garden_root_path,
                    project_dir,
                    name="modelica_project",
                    include_kind=False,
                )
            ],
            candidate_status="candidate",
        )
    except Exception as exc:
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            recipe="modelica",
            status="failed",
            run_dir=run_dir,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            preflight=preflight,
            completed_at=utc_now_iso(),
            error=str(exc),
            candidate_status="candidate",
        )
    _DES_RUNS.upsert(garden_root_path, record, recipe="modelica")
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    project_dir = resolve_des_artifact_path(
        garden_root=garden_root_path,
        manifest=manifest,
        target=modelica_project_target,
        expected_artifact_type=DES_MODELICA_PROJECT_ARTIFACT_TYPE,
        expect_directory=True,
    )
    normalized_run_id = _DES_RUNS.normalize_run_id(run_id, recipe="modelica")
    run_dir = _DES_RUNS.run_dir(garden_root_path, normalized_run_id, recipe="modelica")
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
        target=_DES_RUNS.make_target(manifest.garden_id, normalized_run_id, recipe="modelica"),
        recipe="modelica",
        status=status,
        run_dir=run_dir,
        modelica_project_target=modelica_project_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
        candidate_status="candidate",
    )
    _DES_RUNS.upsert(garden_root_path, record, recipe="modelica")
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_modelica_simulation_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            modelica_project_dir=str(project_dir),
        )
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="modelica") or record
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _DES_RUNS.resolve_run_id(run_target, run_id, recipe=recipe)
    record = _DES_RUNS.get(garden_root_path, resolved_id, recipe=recipe)
    if record is None:
        raise ValueError(f"Dragonfly DES {recipe} run not found: {resolved_id}")
    record = _stabilize_running_record(garden_root_path, recipe, record)
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Dragonfly DES {recipe} run returned: {resolved_id}",
    )


def _run_urbanopt_job(
    *,
    garden_root: str,
    run_id: str,
    feature_geojson: str,
    scenario_csv: str,
    cpu_count: int | None,
    runtime: dict[str, Any] | None = None,
) -> None:
    garden_root_path = require_garden_root(garden_root)
    record = _DES_RUNS.get(garden_root_path, run_id, recipe="urbanopt")
    if record is None:
        return
    try:
        if has_urbanopt_cli_bundle(runtime):
            run_urbanopt_energy_with_cli_bundle(
                feature_geojson=feature_geojson,
                scenario_csv=scenario_csv,
                runtime=runtime,
                cpu_count=cpu_count,
            )
            discovered = []
        else:
            with urbanopt_runtime_env(runtime):
                outputs = sdk_run_urbanopt(feature_geojson, scenario_csv, cpu_count=cpu_count)
            discovered = outputs_from_sdk_result(garden_root_path, outputs, include_kind=False)
        if not discovered:
            discovered = discover_urbanopt_outputs(
                garden_root_path, Path(feature_geojson).parent, include_kind=False
            )
        if not discovered:
            raise RuntimeError("URBANopt run finished without discoverable outputs.")
        failed_job_error = failed_urbanopt_job_error(garden_root_path, Path(feature_geojson).parent)
        if failed_job_error:
            failure = _DES_RUNS.failure_fields(failed_job_error, failed_job_error)
            failure["outputs"] = discovered
            record.update(failure)
            _DES_RUNS.upsert(garden_root_path, record, recipe="urbanopt")
            return
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": discovered,
            }
        )
    except Exception as exc:
        record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
    _DES_RUNS.upsert(garden_root_path, record, recipe="urbanopt")


def _run_sys_param_job(
    *,
    garden_root: str,
    run_id: str,
    feature_geojson: str,
    scenario_csv: str,
    system_parameter_json_target: dict[str, Any] | None,
) -> None:
    garden_root_path = require_garden_root(garden_root)
    record = _DES_RUNS.get(garden_root_path, run_id, recipe="sys_param")
    if record is None:
        return
    try:
        sys_param_path = Path(sdk_run_des_sys_param(feature_geojson, scenario_csv)).resolve()
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": [
                    output_for_path(
                        garden_root_path,
                        sys_param_path,
                        name="system_params",
                        include_kind=False,
                    )
                ],
                "system_parameter_json_target": system_parameter_json_target
                or record.get("system_parameter_json_target", {}),
            }
        )
    except Exception as exc:
        record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
    _DES_RUNS.upsert(garden_root_path, record, recipe="sys_param")


def _run_modelica_simulation_job(
    *,
    garden_root: str,
    run_id: str,
    modelica_project_dir: str,
) -> None:
    garden_root_path = require_garden_root(garden_root)
    record = _DES_RUNS.get(garden_root_path, run_id, recipe="modelica")
    if record is None:
        return
    try:
        result_dir_val = sdk_run_modelica_docker(modelica_project_dir)
        if result_dir_val is None:
            raise ValueError("Expected a Modelica project directory path.")
        result_dir = resolve_existing_garden_path(
            garden_root_path, result_dir_val, kind="directory", label="Dragonfly DES project directory"
        )
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": [
                    output_for_path(
                        garden_root_path,
                        result_dir,
                        name="modelica_results",
                        include_kind=False,
                    )
                ],
            }
        )
    except Exception as exc:
        record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
    _DES_RUNS.upsert(garden_root_path, record, recipe="modelica")


def _resolve_feature_geojson(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        suffix=".geojson",
    )


def _resolve_scenario_csv(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        suffix=".csv",
    )


def _resolve_system_parameter_json(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE,
        suffix=".json",
    )


def _preflight_gmt_runtime() -> dict[str, Any]:
    try:
        des_gmt = get_ladybug_tools_config().get("summary_view", {}).get("engines", {}).get("des_gmt")
    except Exception:
        des_gmt = None
    if isinstance(des_gmt, dict):
        if des_gmt.get("available") is True:
            return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": des_gmt}
        exe = des_gmt.get("exe")
        exe_path = exe.get("path") if isinstance(exe, dict) else None
        missing = [str(item) for item in des_gmt.get("missing", []) if item]
        details = ", ".join(missing) if missing else "DES GMT dependencies"
        return blocked_preflight(
            [f"GMT / uo_des command is not ready at {exe_path}; missing: {details}."],
            missing=["gmt"],
            runtime=des_gmt,
            diagnostics=_des_diagnostics(des_gmt, ["gmt"]),
        )
    scripts_path = Path(str(hb_folders.python_scripts_path or "")).expanduser()
    gmt_exe = scripts_path / ("uo_des.exe" if os.name == "nt" else "uo_des")
    runtime = {"python_scripts_path": str(scripts_path), "gmt_exe": str(gmt_exe)}
    if not gmt_exe.is_file():
        return blocked_preflight(
            [f"GMT / uo_des command was not found at {gmt_exe}."],
            missing=["gmt"],
            runtime={"python_scripts_path": str(scripts_path), "expected_exe": str(gmt_exe)},
            diagnostics=_des_diagnostics({"python_scripts_path": str(scripts_path), "expected_exe": str(gmt_exe)}, ["gmt"]),
        )
    return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": runtime}


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
    runtime = {"gmt": gmt.get("runtime"), "docker": docker, "omc": omc}
    if issues:
        return blocked_preflight(
            issues,
            missing=missing,
            runtime=runtime,
            diagnostics=_des_diagnostics(runtime, missing),
        )
    return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": runtime}


def _des_diagnostics(runtime: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {"network_policy": dict(DEFAULT_DES_NETWORK_POLICY)}
    gmt = runtime.get("gmt") if isinstance(runtime.get("gmt"), dict) else runtime
    if isinstance(gmt, dict):
        diagnostics["des_gmt"] = gmt
    if "docker" in runtime or "omc" in runtime:
        diagnostics["modelica_runtime"] = {
            "docker": runtime.get("docker"),
            "omc": runtime.get("omc"),
            "missing": list(missing),
        }
    return diagnostics


def _write_background_request(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "background_request.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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
    record: dict[str, Any] = {
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


def _stabilize_running_record(garden_root: Path, recipe: str, record: dict[str, Any]) -> dict[str, Any]:
    """Turn abandoned in-process background ledgers into honest blocked records."""
    if record.get("runtime_status") != "running":
        return record
    started = _parse_utc(record.get("started_at") or record.get("created_at"))
    if started is None or (datetime.now(UTC) - started).total_seconds() < STALE_RUNNING_SECONDS:
        return record
    run_folder = record.get("run_folder")
    discovered = (
        discover_urbanopt_outputs(garden_root, garden_root / run_folder, include_kind=False)
        if isinstance(run_folder, str)
        else []
    )
    if discovered:
        return {**record, "outputs": discovered}

    record = dict(record)
    message = (
        "stale running ledger; the original in-process background worker is no "
        "longer active. Restart the run or rerun it with a live MCP process."
    )
    preflight = dict(record.get("preflight") or {})
    issues = list(preflight.get("issues") or [])
    if message not in issues:
        issues.append(message)
    preflight.update(
        {
            "status": "blocked",
            "runtime_status": "blocked",
            "issues": issues,
            "recommended_next_tools": [CONFIG_NEXT_TOOL],
        }
    )
    record.update(
        {
            "status": "blocked",
            "runtime_status": "blocked",
            "completed_at": utc_now_iso(),
            "preflight": preflight,
            "error": message,
        }
    )
    _DES_RUNS.upsert(garden_root, record, recipe=recipe)
    return record


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


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
    poll_tool = {
        "urbanopt": "DF_DES_Poll_URBANopt_Simulation",
        "sys_param": "DF_DES_Poll_Sys_Param",
        "modelica": "DF_DES_Poll_Modelica_Simulation",
    }[record["recipe"]]
    poll_next = {"tool": poll_tool, "arguments": {"garden_root": str(garden_root), "run_target": target}}
    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "recipe": record["recipe"],
        "status": runtime_status,
        "runtime_status": runtime_status,
        "run": _DES_RUNS.public_run(record),
        "outputs": record.get("outputs") or [],
        "poll_next": poll_next,
        "preflight": record.get("preflight"),
        "recommended_next_tools": recommended,
    }
    if record.get("candidate_status"):
        summary_view["candidate_status"] = record["candidate_status"]
    report_details = {"recommended_next_tools": recommended, "preflight": record.get("preflight")}
    attach_runtime_diagnostics(summary_view, report_details, record.get("preflight"))
    result: dict[str, Any] = {
        "target": target,
        "run_target": target,
        "runtime_status": runtime_status,
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status="warning" if runtime_status in {"blocked", "failed"} else "ok",
            message=message,
            warnings=list((record.get("preflight") or {}).get("issues") or []),
            details=report_details,
        ),
    }
    for key in ("system_parameter_json_target", "modelica_project_target"):
        if key in record:
            result[key] = record[key]
    return result
