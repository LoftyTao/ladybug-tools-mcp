"""Garden-managed Dragonfly DES run ledgers and runtime-gated commands."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import time
import traceback
from typing import Any

from dragonfly_energy.des.ghe import GroundHeatExchanger
from dragonfly_energy.run import base_honeybee_osw as sdk_base_honeybee_osw
from dragonfly_energy.run import check_des_compatibility as sdk_check_des_compatibility
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_des_modelica as sdk_run_des_modelica
from dragonfly_energy.run import run_des_sys_param as sdk_run_des_sys_param
from dragonfly_energy.run import run_modelica_docker as sdk_run_modelica_docker
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt
from dragonfly_energy.run import set_building_district_loads as sdk_set_building_district_loads
from honeybee.config import folders as hb_folders

from garden.background import submit_worker_process
from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_des.authoring import load_des_object

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
        "worker_pid",
        "feature_geojson_target",
        "scenario_csv_target",
        "system_parameter_json_target",
        "modelica_project_target",
        "preflight",
        "outputs",
        "error",
    ),
    ledger=RunLedger(
        lock="file",
        atomic=True,
        recover_trailing_json=True,
        empty_is_empty=True,
    ),
)


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
    temp_dir = (garden_root / "tmp" / run_dir.name).resolve()
    temp_dir.relative_to(garden_root)
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    return env


def _record_worker_pid(garden_root: Path, recipe: str, run_id: str, proc: Any) -> None:
    worker_pid = getattr(proc, "pid", None)
    if worker_pid is None:
        return
    current = _DES_RUNS.get(garden_root, run_id, recipe=recipe)
    if current is not None and current.get("worker_pid") is None:
        current["worker_pid"] = worker_pid
        _DES_RUNS.upsert(garden_root, current, recipe=recipe)


def _wait_for_des_run(
    garden_root: str,
    recipe: str,
    result: dict[str, Any],
    wait_seconds: float | None,
    poll_interval: float,
) -> dict[str, Any]:
    requested_wait = max(float(wait_seconds or 0), 0.0)
    if not requested_wait:
        return result
    applied_wait = min(requested_wait, 240.0)
    interval = max(float(poll_interval or 2.0), 0.2)
    deadline = time.monotonic() + applied_wait
    while result.get("runtime_status") in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
        result = _poll_run(
            garden_root=garden_root,
            recipe=recipe,
            run_target=result.get("run_target"),
            run_id=None,
        )
    summary_view = result.setdefault("summary_view", {})
    summary_view["wait_seconds_requested"] = wait_seconds
    summary_view["wait_seconds_applied"] = applied_wait
    return result


def prepare_urbanopt_project(
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
    """Prepare a Garden URBANopt project folder from a feature GeoJSON artifact."""
    from garden.run_urbanopt import _resolve_osw_options

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
    osw_opts = _resolve_osw_options(
        garden_root_path=garden_root_path,
        project_dir=feature_geojson.parent,
        sim_par_target=sim_par_target,
        additional_measures=additional_measures,
        additional_mapper_measures=additional_mapper_measures,
        base_osw=base_osw,
        emissions_year=emissions_year,
    )
    sdk_base_honeybee_osw(
        str(feature_geojson.parent),
        sim_par_json=osw_opts["sim_par_json"],
        additional_measures=osw_opts["additional_measures"],
        additional_mapper_measures=osw_opts["additional_mapper_measures"],
        base_osw=osw_opts["base_osw"],
        epw_file=str(epw_path) if epw_path is not None else None,
        skip_report=False,
        emissions_year=osw_opts["emissions_year"],
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
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start an URBANopt run after runtime preflight and write a DES run ledger."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _DES_RUNS.normalize_run_id(run_id, recipe="urbanopt")
    run_dir = _DES_RUNS.run_dir(garden_root_path, normalized_run_id, recipe="urbanopt")
    preflight = preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status == "blocked":
        _write_background_request(
            run_dir,
            {
                "operation": "run_urbanopt",
                "feature_geojson_target": feature_geojson_target,
                "scenario_csv_target": scenario_csv_target,
                "cpu_count": cpu_count,
            },
        )
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
        try:
            proc = submit_worker_process(
                garden_root=garden_root_path,
                run_dir=run_dir,
                worker_module="garden.dragonfly_des.runs:_run_urbanopt_job",
                request=_json_safe(
                    {
                        "garden_root": str(garden_root_path),
                        "run_id": normalized_run_id,
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "cpu_count": cpu_count,
                        "runtime": preflight.get("runtime"),
                    }
                ),
                cwd=garden_root_path,
                environment=_worker_environment(garden_root_path, run_dir),
            )
            _record_worker_pid(garden_root_path, "urbanopt", normalized_run_id, proc)
        except Exception as exc:
            record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
            _DES_RUNS.upsert(garden_root_path, record, recipe="urbanopt")
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="urbanopt") or record
    result = _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"URBANopt run {latest['runtime_status']}: {normalized_run_id}",
    )
    return _wait_for_des_run(garden_root, "urbanopt", result, wait_seconds, poll_interval)


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


def check_des_compatibility_service(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
) -> dict[str, Any]:
    """Check whether an exported URBANopt project folder is compatible with DES."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    sys_param_exists = (feature_geojson.parent / "system_params.json").is_file()
    issues: list[str] = []
    compatible = True
    try:
        sdk_check_des_compatibility(str(feature_geojson))
    except (AssertionError, ValueError) as exc:
        compatible = False
        issues.append(str(exc))
    return {
        "compatible": compatible,
        "issues": issues,
        "summary_view": {
            "garden_target": manifest.target(),
            "feature_geojson_target": feature_geojson_target,
            "compatible": compatible,
            "system_params_exists": sys_param_exists,
            "issues": issues,
        },
        "report": make_report(
            status="ok" if compatible else "warning",
            message=(
                "URBANopt project is compatible with DES workflow."
                if compatible
                else "URBANopt project failed DES compatibility checks."
            ),
            warnings=issues,
        ),
    }


def bind_des_loads_to_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    scenario_csv_target: dict[str, Any] | None = None,
    heat_exchanger_ets_target: dict[str, Any] | None = None,
    heat_exchanger_ets: dict[str, Any] | None = None,
    heat_pump_ets_target: dict[str, Any] | None = None,
    heat_pump_ets: dict[str, Any] | None = None,
    building_identifiers: list[str] | None = None,
) -> dict[str, Any]:
    """Bind scenario DES loads and/or HeatExchangerETS/HeatPumpETS objects to Dragonfly Buildings."""
    from dragonfly_energy.des.ets import HeatExchangerETS, HeatPumpETS

    if not any(
        val is not None
        for val in (
            scenario_csv_target,
            heat_exchanger_ets_target,
            heat_exchanger_ets,
            heat_pump_ets_target,
            heat_pump_ets,
        )
    ):
        raise ValueError(
            "Provide scenario_csv_target and/or HeatExchangerETS/HeatPumpETS inputs."
        )
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    warnings: list[str] = []
    if scenario_csv_target is not None:
        scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
        warnings = list(model.properties.energy.bind_des_loads_to_buildings(str(scenario_csv)))

    hx_ets_obj = None
    if heat_exchanger_ets_target is not None:
        hx_ets_obj = load_des_object(
            garden_root=garden_root_path,
            target=heat_exchanger_ets_target,
            expected_kind="heat_exchanger_ets",
        )
    elif heat_exchanger_ets is not None:
        hx_ets_obj = (
            HeatExchangerETS.from_dict(heat_exchanger_ets)
            if "type" in heat_exchanger_ets
            else HeatExchangerETS(**heat_exchanger_ets)
        )

    hp_ets_obj = None
    if heat_pump_ets_target is not None:
        hp_ets_obj = load_des_object(
            garden_root=garden_root_path,
            target=heat_pump_ets_target,
            expected_kind="heat_pump_ets",
        )
    elif heat_pump_ets is not None:
        hp_ets_obj = (
            HeatPumpETS.from_dict(heat_pump_ets)
            if "type" in heat_pump_ets
            else HeatPumpETS(**heat_pump_ets)
        )

    wanted_ids = set(building_identifiers) if building_identifiers else None
    target_buildings = [
        bldg
        for bldg in model.buildings
        if wanted_ids is None or bldg.identifier in wanted_ids
    ]
    if wanted_ids is not None and len(target_buildings) != len(wanted_ids):
        missing = sorted(wanted_ids - {b.identifier for b in target_buildings})
        raise ValueError(f"Building(s) not found in Dragonfly Model: {', '.join(missing)}.")
    for bldg in target_buildings:
        if hx_ets_obj is not None:
            bldg.properties.energy.heat_exchanger_ets = hx_ets_obj.duplicate()
        if hp_ets_obj is not None:
            bldg.properties.energy.heat_pump_ets = hp_ets_obj.duplicate()

    updated_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=str(resolved_model_target["model_identifier"]),
        included_prop=["energy", "radiance", "uwg"],
        set_base=manifest.base_dragonfly_model == resolved_model_target,
    )
    building_summaries = [
        {
            "identifier": bldg.identifier,
            "has_des_loads": bool(bldg.properties.energy.has_des_loads),
            "has_heat_exchanger_ets": bldg.properties.energy.heat_exchanger_ets is not None,
            "has_heat_pump_ets": bldg.properties.energy.heat_pump_ets is not None,
        }
        for bldg in model.buildings
    ]
    return {
        "model_target": updated_model_target,
        "buildings": building_summaries,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": updated_model_target,
            "bound_des_loads": scenario_csv_target is not None,
            "assigned_heat_exchanger_ets": hx_ets_obj is not None,
            "assigned_heat_pump_ets": hp_ets_obj is not None,
            "building_count": len(building_summaries),
            "buildings": building_summaries,
            "warning_count": len(warnings),
        },
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type="dragonfly_model",
            artifact_path=persisted_path,
            absolute_path=str((garden_root_path / persisted_path).resolve()),
            source={"operation": "bind_des_loads_to_model"},
        ),
        "report": make_report(
            status="warning" if warnings else "ok",
            message=f"Updated DES loads/ETS on {len(target_buildings)} Dragonfly Building(s).",
            warnings=warnings,
        ),
    }


def read_ghe_results(
    *,
    garden_root: str,
    ghe_target: dict[str, Any] | None = None,
    ghe_folder: str | None = None,
    borehole_file: str | None = None,
    g_function_file: str | None = None,
    summary_file: str | None = None,
    units: str = "Meters",
    ortho_rotation: bool = False,
) -> dict[str, Any]:
    """Read GHEDesigner borehole positions, G-functions, monthly ground temperatures, and E+ properties."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    ghe_obj = (
        load_des_object(
            garden_root=garden_root_path,
            target=ghe_target,
            expected_kind="ground_heat_exchanger",
        )
        if ghe_target is not None
        else None
    )

    folder_path: Path | None = None
    if ghe_folder is not None:
        folder_path = resolve_existing_garden_path(
            garden_root_path,
            ghe_folder,
            kind="directory",
            label="GHE results folder",
        )

    def _find_ghe_file(explicit: str | None, default_name: str, label: str) -> Path | None:
        if explicit is not None:
            return resolve_existing_garden_path(garden_root_path, explicit, kind="file", label=label)
        if folder_path is not None:
            direct = folder_path / default_name
            if direct.is_file():
                return direct
            matches = sorted(folder_path.rglob(default_name))
            if matches:
                return matches[0]
        return None

    b_path = _find_ghe_file(borehole_file, "BoreFieldData.csv", "GHE borehole CSV")
    g_path = _find_ghe_file(g_function_file, "Gfunction.csv", "GHE G-function CSV")
    s_path = _find_ghe_file(summary_file, "SimulationSummary.json", "GHE summary JSON")
    if b_path is None and g_path is None and s_path is None:
        raise ValueError(
            "Provide at least one GHE output file (borehole_file, g_function_file, summary_file) "
            "or a ghe_folder containing BoreFieldData.csv / Gfunction.csv / SimulationSummary.json."
        )

    boreholes: list[list[float]] | None = None
    if b_path is not None:
        if ghe_obj is not None:
            pts = ghe_obj.load_boreholes(
                str(b_path),
                units=units,
                ortho_rotation=ortho_rotation,
            )
            boreholes = [[round(pt.x, 6), round(pt.y, 6)] for pt in pts]
        else:
            lines = b_path.read_text(encoding="utf-8").splitlines()
            boreholes = [
                [float(c) for c in line.split(",")[:2]]
                for line in lines[1:]
                if line.strip()
            ]

    g_function: list[list[float]] | None = None
    if g_path is not None:
        g_function = GroundHeatExchanger.load_g_function(str(g_path))

    monthly_temperatures: list[float] | None = None
    energyplus_properties: dict[str, Any] | None = None
    if s_path is not None:
        monthly_temperatures = GroundHeatExchanger.load_monthly_temperatures(str(s_path))
        prop_values = GroundHeatExchanger.load_energyplus_properties(str(s_path))
        energyplus_properties = dict(
            zip(GroundHeatExchanger.PROPERTY_NAMES, prop_values, strict=False)
        )

    return {
        "boreholes": boreholes,
        "g_function": g_function,
        "monthly_temperatures": monthly_temperatures,
        "energyplus_properties": energyplus_properties,
        "summary_view": {
            "garden_target": manifest.target(),
            "ghe_target": ghe_target,
            "borehole_count": len(boreholes) if boreholes is not None else 0,
            "g_function_points": len(g_function) if g_function is not None else 0,
            "monthly_temperature_count": (
                len(monthly_temperatures) if monthly_temperatures is not None else 0
            ),
            "min_ground_temp_c": (
                round(min(monthly_temperatures), 3) if monthly_temperatures else None
            ),
            "max_ground_temp_c": (
                round(max(monthly_temperatures), 3) if monthly_temperatures else None
            ),
            "energyplus_properties": energyplus_properties,
        },
        "report": make_report(
            status="ok",
            message="Read GHE borehole, G-function, and ground temperature results.",
        ),
    }


def start_sys_param(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    system_parameter_json_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
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
    preflight = _preflight_gmt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status == "blocked":
        _write_background_request(
            run_dir,
            {
                "operation": "run_des_sys_param",
                "feature_geojson_target": feature_geojson_target,
                "scenario_csv_target": scenario_csv_target,
                "system_parameter_json_target": system_parameter_json_target or {},
            },
        )
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
        try:
            proc = submit_worker_process(
                garden_root=garden_root_path,
                run_dir=run_dir,
                worker_module="garden.dragonfly_des.runs:_run_sys_param_job",
                request=_json_safe(
                    {
                        "garden_root": str(garden_root_path),
                        "run_id": normalized_run_id,
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "system_parameter_json_target": system_parameter_json_target,
                    }
                ),
                cwd=garden_root_path,
                environment=_worker_environment(garden_root_path, run_dir),
            )
            _record_worker_pid(garden_root_path, "sys_param", normalized_run_id, proc)
        except Exception as exc:
            record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
            _DES_RUNS.upsert(garden_root_path, record, recipe="sys_param")
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="sys_param") or record
    result = _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"DES system-parameter run {latest['runtime_status']}: {normalized_run_id}",
    )
    return _wait_for_des_run(garden_root, "sys_param", result, wait_seconds, poll_interval)


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
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
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
    preflight = _preflight_modelica_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status == "blocked":
        _write_background_request(
            run_dir,
            {
                "operation": "run_modelica_docker",
                "modelica_project_target": modelica_project_target,
                "candidate_status": "candidate",
            },
        )
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
        try:
            proc = submit_worker_process(
                garden_root=garden_root_path,
                run_dir=run_dir,
                worker_module="garden.dragonfly_des.runs:_run_modelica_simulation_job",
                request=_json_safe(
                    {
                        "garden_root": str(garden_root_path),
                        "run_id": normalized_run_id,
                        "modelica_project_dir": str(project_dir),
                    }
                ),
                cwd=garden_root_path,
                environment=_worker_environment(garden_root_path, run_dir),
            )
            _record_worker_pid(garden_root_path, "modelica", normalized_run_id, proc)
        except Exception as exc:
            record.update(_DES_RUNS.failure_fields(str(exc), traceback.format_exc()))
            _DES_RUNS.upsert(garden_root_path, record, recipe="modelica")
    latest = _DES_RUNS.get(garden_root_path, normalized_run_id, recipe="modelica") or record
    result = _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"Modelica simulation {latest['runtime_status']}: {normalized_run_id}",
    )
    return _wait_for_des_run(garden_root, "modelica", result, wait_seconds, poll_interval)


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
            latest = _DES_RUNS.get(garden_root_path, run_id, recipe="urbanopt") or record
            latest.setdefault("worker_pid", os.getpid())
            latest.update(failure)
            _DES_RUNS.upsert(garden_root_path, latest, recipe="urbanopt")
            return
        updates = {
            "status": "completed",
            "runtime_status": "completed",
            "completed_at": utc_now_iso(),
            "outputs": discovered,
        }
    except Exception as exc:
        updates = _DES_RUNS.failure_fields(str(exc), traceback.format_exc())
    latest = _DES_RUNS.get(garden_root_path, run_id, recipe="urbanopt") or record
    latest.setdefault("worker_pid", os.getpid())
    latest.update(updates)
    _DES_RUNS.upsert(garden_root_path, latest, recipe="urbanopt")


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
        updates = {
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
    except Exception as exc:
        updates = _DES_RUNS.failure_fields(str(exc), traceback.format_exc())
    latest = _DES_RUNS.get(garden_root_path, run_id, recipe="sys_param") or record
    latest.setdefault("worker_pid", os.getpid())
    latest.update(updates)
    _DES_RUNS.upsert(garden_root_path, latest, recipe="sys_param")


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
        updates = {
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
    except Exception as exc:
        updates = _DES_RUNS.failure_fields(str(exc), traceback.format_exc())
    latest = _DES_RUNS.get(garden_root_path, run_id, recipe="modelica") or record
    latest.setdefault("worker_pid", os.getpid())
    latest.update(updates)
    _DES_RUNS.upsert(garden_root_path, latest, recipe="modelica")


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
    """Turn abandoned background ledgers into honest blocked records."""
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
        "stale running ledger; the original background worker is no "
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
    poll_next = {"tool": "GD_Poll_Run", "arguments": {"garden_root": str(garden_root), "run_target": target}}
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
    if record.get("worker_pid") is not None:
        summary_view["worker_pid"] = record["worker_pid"]
        result["worker_pid"] = record["worker_pid"]
    for key in ("system_parameter_json_target", "modelica_project_target"):
        if key in record:
            result[key] = record[key]
    return result
