"""Garden-managed URBANopt Energy run ledger and SDK command services."""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Any

from dragonfly_energy.measure import MapperMeasure
from dragonfly_energy.run import base_honeybee_osw as sdk_base_honeybee_osw
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_default_report as sdk_run_default_report
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt
from honeybee_energy.measure import Measure
from honeybee_energy.result.emissions import emissions_from_sql
from honeybee_energy.result.eui import eui_from_sql
from honeybee_energy.simulation.parameter import SimulationParameter
from ladybug.sql import SQLiteResult

from garden.background import submit_worker_process
from garden.dragonfly_des.export import (
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    resolve_des_artifact_path,
)
from garden.ladybug_tools_config import urbanopt_runtime_env, write_urbanopt_bundle_config
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_energy.config import resolve_garden_weather_epw
from garden.run_ledger import RunManager, serialized_run_start
from garden.urbanopt_cli import (
    CONFIG_NEXT_TOOL,
    DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY,
    attach_runtime_diagnostics,
    discover_urbanopt_outputs,
    failed_urbanopt_job_error,
    has_urbanopt_cli_bundle,
    operation_blocked_result,
    outputs_from_sdk_result,
    preflight_urbanopt_runtime,
    prime_urbanopt_sdk_version_cache,
    run_urbanopt_default_report_with_cli_bundle,
    run_urbanopt_energy_with_cli_bundle,
)
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report
from ladybug_tools_mcp.runtime_home import safe_ascii_temp_dir

URBANOPT_ARTIFACT_DOMAIN = "urbanopt"
URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE = "urbanopt_project_folder"
URBANOPT_RUN_TARGET_TYPE = "urbanopt_run"
URBANOPT_RUN_DOMAIN = "urbanopt"
URBANOPT_RUN_RECIPE = "run_energy"
URBANOPT_RUN_ROOT = Path("runs") / "urbanopt"
URBANOPT_RUN_INDEX = URBANOPT_RUN_ROOT / "index.json"
DEFAULT_URBANOPT_NETWORK_POLICY = DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY

_URBANOPT_RUNS = RunManager(
    domain=URBANOPT_RUN_DOMAIN,
    target_type=URBANOPT_RUN_TARGET_TYPE,
    runs_dir=URBANOPT_RUN_ROOT,
    default_recipe=URBANOPT_RUN_RECIPE,
    allowed_recipes={URBANOPT_RUN_RECIPE},
    run_id_prefix="urbanopt_energy",
    use_uuid_fallback=True,
    slug_lookup=True,
    domain_message="run_target must reference domain 'urbanopt'.",
    missing_message="Pass run_target or run_id.",
    not_found_label="URBANopt Energy",
    public_fields=(
        "run_id",
        "target",
        "recipe",
        "status",
        "runtime_status",
        "created_at",
        "started_at",
        "completed_at",
        "run_folder",
        "worker_pid",
        "prepared_project_target",
        "feature_geojson_target",
        "scenario_csv_target",
        "model_target",
        "preflight",
        "outputs",
        "error",
    ),
)
_URBANOPT_RUN_LEDGER = _URBANOPT_RUNS.ledger


def _resolve_osw_options(
    *,
    garden_root_path: Path,
    project_dir: Path,
    sim_par_target: dict[str, Any] | None = None,
    additional_measures: list[dict[str, Any] | str] | None = None,
    additional_mapper_measures: list[dict[str, Any] | str] | None = None,
    base_osw: str | dict[str, Any] | None = None,
    emissions_year: int | None = None,
) -> dict[str, Any]:
    sim_par_json: str | None = None
    if sim_par_target is not None:
        if isinstance(sim_par_target, dict) and isinstance(sim_par_target.get("path"), str):
            resolved = resolve_existing_garden_path(
                garden_root_path,
                sim_par_target["path"],
                kind="file",
                suffix=".json",
                label="SimulationParameter JSON",
            )
            sim_par_json = str(resolved)
        elif isinstance(sim_par_target, dict):
            sim_par_obj = SimulationParameter.from_dict(sim_par_target)
            sim_par_file = project_dir / "_simulation_parameter.json"
            sim_par_file.write_text(
                json.dumps(sim_par_obj.to_dict(), indent=2),
                encoding="utf-8",
            )
            sim_par_json = str(sim_par_file)
        else:
            raise ValueError("sim_par_target must be a Garden SimulationParameter target or dict.")

    measures: list[Measure] | None = None
    if additional_measures is not None:
        measures = []
        for item in additional_measures:
            if isinstance(item, dict):
                measures.append(Measure.from_dict(item))
            elif isinstance(item, str):
                resolved_dir = resolve_existing_garden_path(
                    garden_root_path,
                    item,
                    kind="directory",
                    label="OpenStudio Measure folder",
                )
                measures.append(Measure(str(resolved_dir)))
            else:
                raise ValueError("additional_measures items must be Measure dicts or Garden paths.")

    mapper_measures: list[MapperMeasure] | None = None
    if additional_mapper_measures is not None:
        mapper_measures = []
        for item in additional_mapper_measures:
            if isinstance(item, dict):
                mapper_measures.append(MapperMeasure.from_dict(item))
            elif isinstance(item, str):
                resolved_dir = resolve_existing_garden_path(
                    garden_root_path,
                    item,
                    kind="directory",
                    label="URBANopt MapperMeasure folder",
                )
                mapper_measures.append(MapperMeasure(str(resolved_dir)))
            else:
                raise ValueError(
                    "additional_mapper_measures items must be MapperMeasure dicts or Garden paths."
                )

    resolved_base_osw: str | None = None
    if base_osw is not None:
        if isinstance(base_osw, str):
            resolved_base_osw = str(
                resolve_existing_garden_path(
                    garden_root_path,
                    base_osw,
                    kind="file",
                    suffix=".osw",
                    label="Base OSW file",
                )
            )
        elif isinstance(base_osw, dict):
            osw_file = project_dir / "_base_workflow.osw"
            osw_file.write_text(json.dumps(base_osw, indent=2), encoding="utf-8")
            resolved_base_osw = str(osw_file)
        else:
            raise ValueError("base_osw must be a Garden-relative .osw path or OSW dictionary.")

    return {
        "sim_par_json": sim_par_json,
        "additional_measures": measures,
        "additional_mapper_measures": mapper_measures,
        "base_osw": resolved_base_osw,
        "emissions_year": int(emissions_year) if emissions_year is not None else None,
    }


@serialized_run_start
def prepare_project(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    weather_target: dict[str, Any] | None = None,
    cpu_count: int | None = None,
    verbose: bool = False,
    sim_par_target: dict[str, Any] | None = None,
    additional_measures: list[dict[str, Any] | str] | None = None,
    additional_mapper_measures: list[dict[str, Any] | str] | None = None,
    base_osw: str | dict[str, Any] | None = None,
    emissions_year: int | None = None,
) -> dict[str, Any]:
    """Prepare a Garden-bounded URBANopt Energy project from a feature GeoJSON."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    project_dir = feature_geojson.parent
    model_target = _model_target_from_targets(manifest, feature_geojson_target)
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
            operation="prepare_project",
            preflight=preflight,
            label="URBANopt Energy",
        )
    prime_urbanopt_sdk_version_cache(preflight)

    runtime = preflight.get("runtime")
    _URBANOPT_RUNS.prepare_folder(
        garden_root_path,
        to_posix_relative(project_dir, garden_root_path),
        model_target=model_target,
    )
    _clear_urbanopt_run_outputs(garden_root_path, project_dir)
    osw_opts = _resolve_osw_options(
        garden_root_path=garden_root_path,
        project_dir=project_dir,
        sim_par_target=sim_par_target,
        additional_measures=additional_measures,
        additional_mapper_measures=additional_mapper_measures,
        base_osw=base_osw,
        emissions_year=emissions_year,
    )
    sdk_base_honeybee_osw(
        str(project_dir),
        sim_par_json=osw_opts["sim_par_json"],
        additional_measures=osw_opts["additional_measures"],
        additional_mapper_measures=osw_opts["additional_mapper_measures"],
        base_osw=osw_opts["base_osw"],
        epw_file=str(epw_path) if epw_path is not None else None,
        skip_report=False,
        emissions_year=osw_opts["emissions_year"],
    )
    write_urbanopt_bundle_config(project_dir, runtime)
    scenario_csv = Path(
        sdk_prepare_urbanopt_folder(
            str(feature_geojson),
            cpu_count=cpu_count,
            verbose=verbose,
        )
    ).expanduser().resolve()
    write_urbanopt_bundle_config(project_dir, runtime)
    scenario_csv = resolve_existing_garden_path(
        garden_root_path, scenario_csv, kind="file", suffix=".csv", label="URBANopt Energy artifact"
    )
    project_dir = resolve_existing_garden_path(
        garden_root_path, scenario_csv.parent, kind="directory", label="URBANopt Energy project folder"
    )
    project_target = _artifact_target(
        manifest=manifest,
        garden_root=garden_root_path,
        domain=URBANOPT_ARTIFACT_DOMAIN,
        identifier=f"{slugify_name(project_dir.name)}_urbanopt_project",
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        path=project_dir,
        model_target=model_target,
    )
    scenario_target = _artifact_target(
        manifest=manifest,
        garden_root=garden_root_path,
        domain="dragonfly_des",
        identifier=f"{slugify_name(scenario_csv.stem)}_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=scenario_csv,
        model_target=model_target,
    )
    for target in (project_target, scenario_target):
        manifest.upsert_artifact(target, key_fields=("domain", "artifact_type", "identifier"))
    manifest.write(garden_root_path)

    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        artifact_path=project_target["path"],
        absolute_path=str(project_dir),
        source={
            "feature_geojson_target": feature_geojson_target,
            "model_target": model_target,
        },
    )
    summary_view = {
        "garden_target": manifest.target(),
        "prepared": True,
        "runtime_status": "ready",
        "feature_geojson_target": feature_geojson_target,
        "project_folder_target": project_target,
        "scenario_csv_target": scenario_target,
        "preflight": preflight,
    }
    if model_target is not None:
        summary_view["model_target"] = model_target
    if weather_target is not None:
        summary_view["weather_target"] = weather_target
    return {
        "target": project_target,
        "project_folder_target": project_target,
        "scenario_csv_target": scenario_target,
        "runtime_status": "ready",
        "summary_view": summary_view,
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message="Prepared URBANopt Energy project folder.",
        ),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _worker_environment(garden_root: Path, run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    temp_dir = safe_ascii_temp_dir(garden_root, run_dir.name)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    return env


def _record_worker_pid(garden_root: Path, run_id: str, proc: Any) -> None:
    worker_pid = getattr(proc, "pid", None)
    if worker_pid is None:
        return
    current = _URBANOPT_RUNS.get(garden_root, run_id)
    if current is not None and current.get("worker_pid") is None:
        current["worker_pid"] = worker_pid
        _URBANOPT_RUNS.upsert(garden_root, current)


def start_simulation(
    *,
    garden_root: str,
    prepared_project_target: dict[str, Any],
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    cpu_count: int | None = None,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start an URBANopt Energy run and write a Garden run ledger."""
    result = _start_simulation_locked(
        garden_root=garden_root,
        prepared_project_target=prepared_project_target,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        run_id=run_id,
        cpu_count=cpu_count,
    )
    requested_wait = max(float(wait_seconds or 0), 0.0)
    if not requested_wait:
        return result
    applied_wait = min(requested_wait, 240.0)
    interval = max(float(poll_interval or 2.0), 0.2)
    deadline = time.monotonic() + applied_wait
    while result.get("runtime_status") in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
        result = poll_simulation(
            garden_root=garden_root,
            run_target=result.get("run_target"),
        )
    summary_view = result.setdefault("summary_view", {})
    summary_view["wait_seconds_requested"] = wait_seconds
    summary_view["wait_seconds_applied"] = applied_wait
    return result


@serialized_run_start
def _start_simulation_locked(
    *,
    garden_root: str,
    prepared_project_target: dict[str, Any],
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    cpu_count: int | None = None,
) -> dict[str, Any]:
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_run_id = _URBANOPT_RUNS.normalize_run_id(run_id)
    existing = _URBANOPT_RUNS.get(garden_root_path, normalized_run_id)
    if existing is not None:
        return _result_from_record(
            garden_root=garden_root_path,
            manifest=manifest,
            record=existing,
            message=f"URBANopt Energy run already exists: {normalized_run_id}",
        )
    project_dir = _resolve_project_folder(garden_root_path, manifest, prepared_project_target)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    if feature_geojson.parent != project_dir or scenario_csv.parent != project_dir:
        raise ValueError("URBANopt feature, scenario and prepared project must share one folder.")
    model_target = _model_target_from_targets(
        manifest,
        feature_geojson_target,
        prepared_project_target,
    )
    target = _URBANOPT_RUNS.make_target(manifest.garden_id, normalized_run_id)
    preflight = preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status != "blocked":
        prime_urbanopt_sdk_version_cache(preflight)
        _URBANOPT_RUNS.prepare_folder(
            garden_root_path,
            to_posix_relative(project_dir, garden_root_path),
            recipe=URBANOPT_RUN_RECIPE,
            model_target=model_target,
        )
        _clear_urbanopt_run_outputs(garden_root_path, project_dir)
    started_at = utc_now_iso()
    record: dict[str, Any] = {
        "run_id": normalized_run_id,
        "target": target,
        "recipe": URBANOPT_RUN_RECIPE,
        "status": status,
        "runtime_status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(project_dir, garden_root_path),
        "prepared_project_target": prepared_project_target,
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "preflight": preflight,
        "outputs": [],
    }
    if model_target is not None:
        record["model_target"] = model_target
    if status == "blocked":
        record["completed_at"] = utc_now_iso()
        if preflight["issues"]:
            record["error"] = "; ".join(preflight["issues"])
    _URBANOPT_RUNS.upsert(garden_root_path, record)
    if status != "blocked":
        try:
            proc = submit_worker_process(
                garden_root=garden_root_path,
                run_dir=project_dir,
                worker_module="garden.run_urbanopt:_run_urbanopt_job",
                request=_json_safe(
                    {
                        "garden_root": str(garden_root_path),
                        "run_id": normalized_run_id,
                        "project_dir": str(project_dir),
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "cpu_count": cpu_count,
                        "runtime": preflight.get("runtime"),
                    }
                ),
                cwd=garden_root_path,
                environment=_worker_environment(garden_root_path, project_dir),
            )
            _record_worker_pid(garden_root_path, normalized_run_id, proc)
        except Exception as exc:
            record.update(_URBANOPT_RUNS.failure_fields(str(exc), traceback.format_exc()))
            _URBANOPT_RUNS.upsert(garden_root_path, record)
    latest = _URBANOPT_RUNS.get(garden_root_path, normalized_run_id) or record
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"URBANopt Energy run {latest['runtime_status']}: {normalized_run_id}",
    )


def poll_simulation(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one URBANopt Energy run ledger record."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _URBANOPT_RUNS.resolve_run_id(run_target, run_id, recipe=URBANOPT_RUN_RECIPE)
    record = _URBANOPT_RUNS.require(garden_root_path, resolved_id)
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"URBANopt Energy run {record['runtime_status']}: {resolved_id}",
    )


def list_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List output files for one URBANopt Energy run ledger record."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _URBANOPT_RUNS.resolve_run_id(run_target, run_id, recipe=URBANOPT_RUN_RECIPE)
    record = _URBANOPT_RUNS.require(garden_root_path, resolved_id)
    outputs = list(record.get("outputs") or [])
    return {
        "matches": outputs,
        "outputs": outputs,
        "run_target": record["target"],
        "runtime_status": record["runtime_status"],
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_id,
            "recipe": URBANOPT_RUN_RECIPE,
            "runtime_status": record["runtime_status"],
            "count": len(outputs),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(outputs)} output(s) for URBANopt Energy run {resolved_id}.",
        ),
    }


def _run_urbanopt_job(
    *,
    garden_root: str,
    run_id: str,
    project_dir: str,
    feature_geojson: str,
    scenario_csv: str,
    cpu_count: int | None,
    runtime: dict[str, Any] | None = None,
) -> None:
    garden_root_path = require_garden_root(garden_root)
    record = _URBANOPT_RUNS.get(garden_root_path, run_id)
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
            discovered = outputs_from_sdk_result(garden_root_path, outputs)
        if not discovered:
            discovered = discover_urbanopt_outputs(garden_root_path, Path(project_dir))
        if not discovered:
            raise RuntimeError("URBANopt run finished without discoverable outputs.")
        failed_job_error = failed_urbanopt_job_error(garden_root_path, Path(project_dir))
        if failed_job_error:
            failure = _URBANOPT_RUNS.failure_fields(failed_job_error, failed_job_error)
            failure["outputs"] = discovered
            latest = _URBANOPT_RUNS.get(garden_root_path, run_id) or record
            latest.setdefault("worker_pid", os.getpid())
            latest.update(failure)
            _URBANOPT_RUNS.upsert(garden_root_path, latest)
            return
        updates = {
            "status": "completed",
            "runtime_status": "completed",
            "completed_at": utc_now_iso(),
            "outputs": discovered,
        }
    except Exception as exc:
        updates = _URBANOPT_RUNS.failure_fields(str(exc), traceback.format_exc())
    latest = _URBANOPT_RUNS.get(garden_root_path, run_id) or record
    latest.setdefault("worker_pid", os.getpid())
    latest.update(updates)
    _URBANOPT_RUNS.upsert(garden_root_path, latest)


def _clear_urbanopt_run_outputs(garden_root: Path, project_dir: Path) -> None:
    garden_root = garden_root.expanduser().resolve()
    project_dir = project_dir.expanduser().resolve()
    try:
        project_dir.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("URBANopt project folder must stay inside the Garden.") from exc
    for name in ("run", "osm"):
        path = (project_dir / name).resolve()
        path.relative_to(project_dir)
        if path.is_dir():
            shutil.rmtree(path)


def _model_target_from_targets(
    manifest: GardenManifest,
    *targets: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for target in targets:
        if isinstance(target, dict) and isinstance(target.get("model_target"), dict):
            return target["model_target"]
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("path"), str):
            continue
        for artifact in manifest.artifacts:
            if artifact.get("path") == target["path"] and isinstance(artifact.get("model_target"), dict):
                return artifact["model_target"]
    return None


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


def _resolve_project_folder(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    if not isinstance(target, dict):
        raise ValueError("Expected an URBANopt project folder target dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("URBANopt project target must have target_type 'artifact'.")
    if target.get("domain") != URBANOPT_ARTIFACT_DOMAIN:
        raise ValueError("URBANopt project target must reference domain 'urbanopt'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("URBANopt project target belongs to a different Garden.")
    if target.get("artifact_type") != URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE:
        raise ValueError("Expected URBANopt artifact type 'urbanopt_project_folder'.")
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("URBANopt project target requires a non-empty path.")
    if Path(path_value).is_absolute():
        raise ValueError("URBANopt project target path must be Garden-relative.")
    return resolve_existing_garden_path(
        garden_root,
        path_value,
        kind="directory",
        label="URBANopt project folder",
    )


def _artifact_target(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    domain: str,
    identifier: str,
    artifact_type: str,
    path: Path,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": "artifact",
        "domain": domain,
        "garden_id": manifest.garden_id,
        "artifact_type": artifact_type,
        "identifier": identifier,
        "path": to_posix_relative(path, garden_root),
    }
    if model_target is not None:
        target["model_target"] = model_target
    return target


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
        "tool": "GD_Poll_Run",
        "arguments": {"garden_root": str(garden_root), "run_target": target},
    }
    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "recipe": record["recipe"],
        "status": runtime_status,
        "runtime_status": runtime_status,
        "run": _URBANOPT_RUNS.public_run(record),
        "outputs": record.get("outputs") or [],
        "poll_next": poll_next,
        "preflight": record.get("preflight"),
        "recommended_next_tools": recommended,
    }
    report_status = "warning" if runtime_status in {"blocked", "failed"} else "ok"
    report_details = {
        "recommended_next_tools": recommended,
        "preflight": record.get("preflight"),
    }
    attach_runtime_diagnostics(summary_view, report_details, record.get("preflight"))
    result: dict[str, Any] = {
        "target": target,
        "run_target": target,
        "runtime_status": runtime_status,
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status=report_status,
            message=message,
            warnings=list((record.get("preflight") or {}).get("issues") or []),
            details=report_details,
        ),
    }
    if record.get("worker_pid") is not None:
        summary_view["worker_pid"] = record["worker_pid"]
        result["worker_pid"] = record["worker_pid"]
    return result


def _extract_building_sql_summary(
    sql_path: Path,
    *,
    building_id: str,
    subregion: str | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "building_id": building_id,
        "sql_path": str(sql_path),
    }
    eui_data = eui_from_sql(str(sql_path), absolute=False)
    summary.update(
        {
            "eui_kwh_m2": eui_data.get("eui"),
            "total_floor_area_m2": eui_data.get("total_floor_area"),
            "conditioned_floor_area_m2": eui_data.get("conditioned_floor_area"),
            "total_energy_kwh": eui_data.get("total_energy"),
            "end_uses_kwh_m2": dict(eui_data.get("end_uses") or {}),
        }
    )
    sql_obj = SQLiteResult(str(sql_path))
    peak_kw: float | None = None
    for table_name in (
        "Demand End Use Components Summary",
        "Component Sizing Summary",
        "Annual Building Utility Performance Summary",
    ):
        try:
            tabular = sql_obj.tabular_data_by_name(table_name)
        except Exception:
            tabular = {}
        if tabular:
            for row_key, row_vals in tabular.items():
                if "total end uses" in str(row_key).lower() and row_vals:
                    try:
                        val = float(row_vals[0])
                        peak_kw = round(val / 1000.0 if val > 10000 else val, 4)
                    except (TypeError, ValueError):
                        pass
                    break
        if peak_kw is not None:
            break
    if peak_kw is not None:
        summary["peak_electric_kw"] = peak_kw
    if subregion is not None:
        try:
            summary["emissions"] = emissions_from_sql(str(sql_path), subregion=subregion)
        except Exception:
            pass
    return summary


_MAX_URBANOPT_CSV_PREVIEW_ROWS = 24
_MAX_URBANOPT_REPORT_JSON_BYTES = 64 * 1024
_MAX_URBANOPT_RAW_LOAD_BYTES = 50 * 1024 * 1024
_MAX_URBANOPT_COMPACT_LIST_ITEMS = 12
_MAX_URBANOPT_COMPACT_DICT_KEYS = 48
_URBANOPT_LARGE_SEQUENCE_KEYS = {
    "hourly",
    "timeseries",
    "timesteps",
    "power_distribution",
    "power_distribution_results",
    "feature_reports",
    "features",
    "data",
}


def _compact_urbanopt_value(
    value: Any,
    *,
    key_hint: str = "",
    depth: int = 0,
) -> tuple[Any, bool]:
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    if isinstance(value, str):
        if len(value) > 2048:
            return f"{value[:512]}... [truncated {len(value)} chars]", True
        return value, False
    if isinstance(value, list):
        limit = 3 if key_hint.lower() in _URBANOPT_LARGE_SEQUENCE_KEYS else _MAX_URBANOPT_COMPACT_LIST_ITEMS
        if depth >= 4 and len(value) > 3:
            limit = 3
        truncated = len(value) > limit
        items: list[Any] = []
        for elem in value[:limit]:
            compacted, child_trunc = _compact_urbanopt_value(elem, depth=depth + 1)
            truncated = truncated or child_trunc
            items.append(compacted)
        return items, truncated
    if isinstance(value, dict):
        if depth >= 5:
            return {"truncated": True, "key_count": len(value)}, True
        out: dict[str, Any] = {}
        truncated = len(value) > _MAX_URBANOPT_COMPACT_DICT_KEYS
        for idx, (raw_k, raw_v) in enumerate(value.items()):
            if idx >= _MAX_URBANOPT_COMPACT_DICT_KEYS:
                out["_truncated_keys"] = len(value) - _MAX_URBANOPT_COMPACT_DICT_KEYS
                break
            k = str(raw_k)
            compacted, child_trunc = _compact_urbanopt_value(raw_v, key_hint=k, depth=depth + 1)
            truncated = truncated or child_trunc
            out[k] = compacted
            if isinstance(raw_v, list) and child_trunc:
                out[f"{k}_count"] = len(raw_v)
        return out, truncated
    text = str(value)
    if len(text) > 512:
        return f"{text[:512]}...", True
    return text, False


def _summarize_urbanopt_report_json(report_json: Path) -> tuple[dict[str, Any] | None, bool]:
    if not report_json.is_file():
        return None, False
    file_size = report_json.stat().st_size
    if file_size > _MAX_URBANOPT_RAW_LOAD_BYTES:
        return {
            "truncated": True,
            "original_bytes": file_size,
            "note": "default_scenario_report.json exceeds direct load limit; read file on disk for full data.",
        }, True

    parsed = json.loads(report_json.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        return {"value": parsed}, False
    if file_size <= _MAX_URBANOPT_REPORT_JSON_BYTES:
        return parsed, False

    compacted, truncated = _compact_urbanopt_value(parsed)
    assert isinstance(compacted, dict)
    serialized = json.dumps(compacted, ensure_ascii=False).encode("utf-8")
    if len(serialized) > _MAX_URBANOPT_REPORT_JSON_BYTES:
        sr = compacted.get("scenario_report")
        slim: dict[str, Any] = {"truncated": True, "original_bytes": file_size}
        if isinstance(sr, dict):
            slim_sr: dict[str, Any] = {}
            for k, v in sr.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    slim_sr[k] = v
            if isinstance(sr.get("reporting_periods"), list):
                kept_periods = [
                    {pk: pv for pk, pv in period.items() if isinstance(pv, (str, int, float, bool)) or pv is None}
                    if isinstance(period, dict)
                    else period
                    for period in sr["reporting_periods"][:2]
                ]
                if len(json.dumps(kept_periods, ensure_ascii=False).encode("utf-8")) <= _MAX_URBANOPT_REPORT_JSON_BYTES // 2:
                    slim_sr["reporting_periods"] = kept_periods
            slim["scenario_report"] = slim_sr
        return slim, True
    compacted["truncated"] = truncated
    return compacted, truncated


def read_urbanopt_results(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_default_report: bool = True,
    include_building_sql_summary: bool = True,
    subregion: str | None = None,
) -> dict[str, Any]:
    """Generate/read URBANopt default scenario reports and per-building EnergyPlus SQL summaries."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    project_dir = feature_geojson.parent
    run_root = project_dir / "run"
    scenario_dir = run_root / scenario_csv.stem
    if not scenario_dir.is_dir():
        lower_dir = run_root / scenario_csv.stem.lower()
        if lower_dir.is_dir():
            scenario_dir = lower_dir

    report_csv = scenario_dir / "default_scenario_report.csv"
    report_json = scenario_dir / "default_scenario_report.json"
    warnings: list[str] = []

    if run_default_report:
        preflight = preflight_urbanopt_runtime()
        if preflight["runtime_status"] != "blocked":
            prime_urbanopt_sdk_version_cache(preflight)
            runtime = preflight.get("runtime")
            write_urbanopt_bundle_config(project_dir, runtime)
            if has_urbanopt_cli_bundle(runtime):
                r_csv, r_json = run_urbanopt_default_report_with_cli_bundle(
                    feature_geojson=str(feature_geojson),
                    scenario_csv=str(scenario_csv),
                    runtime=runtime,
                )
            else:
                with urbanopt_runtime_env(runtime):
                    raw_csv, raw_json = sdk_run_default_report(
                        str(feature_geojson),
                        str(scenario_csv),
                    )
                    r_csv, r_json = Path(raw_csv), Path(raw_json)
            report_csv, report_json = r_csv, r_json
        elif not report_csv.is_file() and not report_json.is_file():
            return operation_blocked_result(
                garden_root=garden_root_path,
                manifest=manifest,
                operation="read_urbanopt_results",
                preflight=preflight,
                label="URBANopt Energy",
            )
        else:
            warnings.append(
                "URBANopt CLI unavailable; read existing default_scenario_report files on disk."
            )

    scenario_report_data, scenario_report_truncated = _summarize_urbanopt_report_json(report_json)

    csv_rows: list[dict[str, Any]] = []
    csv_columns: list[str] = []
    csv_row_count = 0
    if report_csv.is_file():
        with report_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            csv_columns = list(reader.fieldnames or [])
            for row in reader:
                csv_row_count += 1
                if len(csv_rows) < _MAX_URBANOPT_CSV_PREVIEW_ROWS:
                    csv_rows.append(row)
    csv_rows_truncated = csv_row_count > len(csv_rows)

    buildings_summary: list[dict[str, Any]] = []
    if include_building_sql_summary and scenario_dir.is_dir():
        for entry in sorted(scenario_dir.iterdir()):
            if not entry.is_dir():
                continue
            for candidate_sql in (entry / "eplusout.sql", entry / "in.sql"):
                if candidate_sql.is_file():
                    try:
                        buildings_summary.append(
                            _extract_building_sql_summary(
                                candidate_sql,
                                building_id=entry.name,
                                subregion=subregion,
                            )
                        )
                    except Exception as exc:
                        warnings.append(
                            f"Could not parse SQL summary for building '{entry.name}': {exc}"
                        )
                    break

    total_area = sum(float(b.get("total_floor_area_m2") or 0.0) for b in buildings_summary)
    total_energy = sum(float(b.get("total_energy_kwh") or 0.0) for b in buildings_summary)
    district_eui = round(total_energy / total_area, 3) if total_area > 0 else None

    if scenario_report_data is None and not csv_row_count and not buildings_summary:
        raise ValueError(
            "No URBANopt scenario reports or building SQL results were found under "
            f"{to_posix_relative(scenario_dir, garden_root_path)}."
        )

    scenario_info = (
        scenario_report_data.get("scenario_report")
        if isinstance(scenario_report_data, dict)
        else None
    )
    report_json_rel = to_posix_relative(report_json, garden_root_path) if report_json.is_file() else None
    report_csv_rel = to_posix_relative(report_csv, garden_root_path) if report_csv.is_file() else None
    summary_view = {
        "garden_target": manifest.target(),
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "report_json_path": report_json_rel,
        "report_csv_path": report_csv_rel,
        "scenario_report": scenario_info or scenario_report_data,
        "scenario_report_truncated": scenario_report_truncated,
        "csv_columns": csv_columns,
        "csv_row_count": csv_row_count,
        "csv_rows_truncated": csv_rows_truncated,
        "building_count": len(buildings_summary),
        "total_floor_area_m2": round(total_area, 3) if buildings_summary else None,
        "total_energy_kwh": round(total_energy, 3) if buildings_summary else None,
        "district_eui_kwh_m2": district_eui,
    }
    return {
        "report_json_path": report_json_rel,
        "report_csv_path": report_csv_rel,
        "scenario_report": scenario_report_data,
        "scenario_info": scenario_info,
        "scenario_report_truncated": scenario_report_truncated,
        "csv_columns": csv_columns,
        "csv_row_count": csv_row_count,
        "csv_rows": csv_rows,
        "csv_rows_truncated": csv_rows_truncated,
        "buildings": buildings_summary,
        "summary_view": summary_view,
        "report": make_report(
            status="warning" if warnings else "ok",
            message=(
                f"Read URBANopt results ({len(buildings_summary)} building SQL summary(s), "
                f"{csv_row_count} CSV row(s))."
            ),
            warnings=warnings,
        ),
    }


__all__ = [
    "DEFAULT_URBANOPT_NETWORK_POLICY",
    "URBANOPT_ARTIFACT_DOMAIN",
    "URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE",
    "URBANOPT_RUN_DOMAIN",
    "URBANOPT_RUN_INDEX",
    "URBANOPT_RUN_RECIPE",
    "URBANOPT_RUN_ROOT",
    "URBANOPT_RUN_TARGET_TYPE",
    "_URBANOPT_RUN_LEDGER",
    "list_run_outputs",
    "poll_simulation",
    "prepare_project",
    "read_urbanopt_results",
    "start_simulation",
]
