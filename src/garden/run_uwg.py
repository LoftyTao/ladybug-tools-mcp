"""Garden-managed Dragonfly UWG Alternative Weather parameters, writer, and runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any
from uuid import uuid4

import dragonfly_uwg._extend_dragonfly  # noqa: F401
from dragonfly_uwg.simulation.boundary import BoundaryLayerParameter
from dragonfly_uwg.simulation.parameter import UWGSimulationParameter
from dragonfly_uwg.simulation.refsite import ReferenceEPWSite
from dragonfly_uwg.simulation.runperiod import UWGRunPeriod
from dragonfly_uwg.simulation.vegetation import VegetationParameter
from dragonfly_uwg.writer import model_to_uwg as sdk_model_to_uwg
from honeybee.config import folders as hb_folders
from ladybug.dt import Date
from ladybug.epw import EPW

from garden.background import submit_worker_process

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_energy.config import make_garden_weather_target
from garden.run_ledger import RunLedger, RunManager
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

UWG_DOMAIN = "dragonfly_uwg"
UWG_ARTIFACT_DIR = Path("artifacts") / "uwg"
UWG_PARAMETER_TARGET_TYPE = "uwg_simulation_parameter"
UWG_JSON_ARTIFACT_TYPE = "uwg_json"
UWG_RUN_TARGET_TYPE = "uwg_run"
UWG_RUN_RECIPE = "urban_weather_generator"

PARAMETERS_DIR = UWG_ARTIFACT_DIR / "parameters"
UWG_JSON_DIR = UWG_ARTIFACT_DIR / "json"
UWG_RUNS_DIR = Path("runs") / "uwg"
UWG_RUN_INDEX = UWG_RUNS_DIR / "index.json"
OUTPUT_NAMES = ("uwg_json", "morphed_epw", "weather_target", "stdio_log")
UWG_CLI_TIMEOUT_SECONDS = 900

_UWG_RUNS = RunManager(
    domain=UWG_DOMAIN,
    target_type=UWG_RUN_TARGET_TYPE,
    runs_dir=UWG_RUNS_DIR,
    default_recipe=UWG_RUN_RECIPE,
    allowed_recipes={UWG_RUN_RECIPE},
    use_uuid_fallback=True,
    slug_lookup=True,
    validate_target_domain=False,
    missing_message="Pass run_target or run_id.",
    not_found_label="UWG",
    public_fields=(
        "run_id",
        "target",
        "recipe",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "run_folder",
        "worker_pid",
        "model_target",
        "weather_target",
        "simulation_parameter_target",
        "preflight",
        "outputs",
        "error",
    ),
    include_missing_public=True,
    ledger=RunLedger(
        lock="file",
        atomic=True,
        recover_trailing_json=True,
        empty_is_empty=True,
        ensure_ascii=True,
    ),
)


# ---------------------------------------------------------------------------
# UWG simulation parameters
# ---------------------------------------------------------------------------


def create_uwg_simulation_parameter(
    *,
    garden_root: str,
    identifier: str | None = None,
    climate_zone: str | None = None,
    run_period: dict[str, Any] | None = None,
    timestep: int = 12,
    vegetation_parameter: dict[str, Any] | None = None,
    reference_epw_site: dict[str, Any] | None = None,
    boundary_layer_parameter: dict[str, Any] | None = None,
    save: bool = True,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and optionally persist a UWGSimulationParameter."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    parameter = _build_parameter(
        climate_zone=climate_zone,
        run_period=run_period,
        timestep=timestep,
        vegetation_parameter=vegetation_parameter,
        reference_epw_site=reference_epw_site,
        boundary_layer_parameter=boundary_layer_parameter,
    )
    object_dict = parameter.to_dict()
    result: dict[str, Any] = {
        "summary_view": _parameter_summary(object_dict),
        "report": make_report(status="ok", message="Created UWG simulation parameter."),
    }
    if include_body or not save:
        result["object_dict"] = object_dict
    if not save:
        return result

    identifier_value = slugify_name(identifier or "uwg_simulation_parameter")
    output_dir = garden_root_path / PARAMETERS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{identifier_value}.json"
    output_path.write_text(json.dumps(object_dict, indent=2) + "\n", encoding="utf-8")
    target = make_uwg_simulation_parameter_target(
        garden_id=manifest.garden_id,
        identifier=identifier_value,
        path=to_posix_relative(output_path, garden_root_path),
    )
    artifact = {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "artifact_type": "uwg_simulation_parameter",
        "identifier": identifier_value,
        "path": target["path"],
        "source": target,
    }
    manifest.upsert_artifact(artifact, key_fields=("artifact_type", "identifier"))
    manifest.write(garden_root_path)
    result.update(
        {
            "target": target,
            "uwg_simulation_parameter_target": target,
            "artifact_receipt": make_artifact_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                artifact_type="uwg_simulation_parameter",
                artifact_path=target["path"],
                absolute_path=str(output_path),
                source=target,
            ),
        }
    )
    result["summary_view"]["target"] = target
    return result


def make_uwg_simulation_parameter_target(
    *,
    garden_id: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a persisted UWG simulation parameter target."""
    return {
        "target_type": UWG_PARAMETER_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": UWG_DOMAIN,
        "identifier": identifier,
        "path": path,
    }


def normalize_uwg_simulation_parameter_target(value: Any) -> dict[str, Any]:
    """Validate a UWG simulation parameter target."""
    if not isinstance(value, dict):
        raise ValueError("UWG simulation parameter target must be a dictionary.")
    if value.get("target_type") != UWG_PARAMETER_TARGET_TYPE:
        raise ValueError(
            f"UWG simulation parameter target must have target_type {UWG_PARAMETER_TARGET_TYPE!r}."
        )
    if value.get("domain") != UWG_DOMAIN:
        raise ValueError("UWG simulation parameter target must have domain 'dragonfly_uwg'.")
    if not value.get("path"):
        raise ValueError("UWG simulation parameter target requires path.")
    return dict(value)


def load_uwg_simulation_parameter(
    *,
    garden_root: Path,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
) -> tuple[UWGSimulationParameter | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve a target or inline dictionary to a UWGSimulationParameter."""
    if simulation_parameter_target is not None and simulation_parameter is not None:
        raise ValueError("Pass either simulation_parameter_target or simulation_parameter, not both.")
    if simulation_parameter_target is not None:
        target = normalize_uwg_simulation_parameter_target(simulation_parameter_target)
        path = resolve_existing_garden_path(
            garden_root,
            str(target["path"]),
            kind="file",
            label="UWG simulation parameter",
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        return UWGSimulationParameter.from_dict(data), target, data
    if simulation_parameter is not None:
        return UWGSimulationParameter.from_dict(simulation_parameter), None, simulation_parameter
    return None, None, None


def _coerce_uwg_param(cls: type, value: dict[str, Any]) -> Any:
    return cls.from_dict(value) if "type" in value else cls(**value)


def _build_parameter(
    *,
    climate_zone: str | None,
    run_period: dict[str, Any] | None,
    timestep: int,
    vegetation_parameter: dict[str, Any] | None,
    reference_epw_site: dict[str, Any] | None,
    boundary_layer_parameter: dict[str, Any] | None,
) -> UWGSimulationParameter:
    kwargs: dict[str, Any] = {"timestep": timestep}
    if climate_zone is not None:
        kwargs["climate_zone"] = climate_zone
    if run_period is not None:
        kwargs["run_period"] = _run_period_from_input(run_period)
    if vegetation_parameter is not None:
        kwargs["vegetation_parameter"] = _coerce_uwg_param(
            VegetationParameter, vegetation_parameter
        )
    if reference_epw_site is not None:
        kwargs["reference_epw_site"] = _coerce_uwg_param(
            ReferenceEPWSite, reference_epw_site
        )
    if boundary_layer_parameter is not None:
        kwargs["boundary_layer_parameter"] = _coerce_uwg_param(
            BoundaryLayerParameter, boundary_layer_parameter
        )
    return UWGSimulationParameter(**kwargs)


def _run_period_from_input(value: dict[str, Any] | None) -> UWGRunPeriod | None:
    if value is None:
        return None
    if value.get("type") == "UWGRunPeriod":
        return UWGRunPeriod.from_dict(value)
    return UWGRunPeriod(
        start_date=Date(int(value["start_month"]), int(value["start_day"])),
        end_date=Date(int(value["end_month"]), int(value["end_day"])),
    )


def _parameter_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": data.get("type"),
        "climate_zone": data.get("climate_zone"),
        "timestep": data.get("timestep"),
        "run_period": data.get("run_period") or {},
        "has_vegetation_parameter": bool(data.get("vegetation_parameter")),
        "has_reference_epw_site": bool(data.get("reference_epw_site")),
        "has_boundary_layer_parameter": bool(data.get("boundary_layer_parameter")),
    }


# ---------------------------------------------------------------------------
# UWG JSON writer & EPW path resolution
# ---------------------------------------------------------------------------


def dragonfly_model_to_uwg(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Write a UWG JSON artifact from a Dragonfly model and EPW."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    resolved_epw = resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
    )
    parameter, parameter_target, parameter_dict = load_uwg_simulation_parameter(
        garden_root=garden_root_path,
        simulation_parameter_target=simulation_parameter_target,
        simulation_parameter=simulation_parameter,
    )
    uwg_dict = sdk_model_to_uwg(model, str(resolved_epw), simulation_parameter=parameter)
    identifier = slugify_name(name or f"{model.identifier}_uwg")
    output_dir = garden_root_path / UWG_JSON_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{identifier}.json"
    output_path.write_text(json.dumps(uwg_dict, indent=2) + "\n", encoding="utf-8")
    target = make_uwg_json_artifact_target(
        manifest=manifest,
        identifier=identifier,
        path=to_posix_relative(output_path, garden_root_path),
    )
    manifest.upsert_artifact(target, key_fields=("artifact_type", "identifier"))
    manifest.write(garden_root_path)

    summary_view: dict[str, Any] = {
        "target": target,
        "uwg_json_artifact_target": target,
        "model_target": resolved_model_target,
        "weather_target": weather_target or {},
        "epw_path": to_posix_relative(resolved_epw, garden_root_path),
        "simulation_parameter_target": parameter_target,
        "has_simulation_parameter": parameter is not None,
        "path": target["path"],
    }
    if parameter_dict is not None:
        summary_view["simulation_parameter_summary"] = {
            "timestep": parameter_dict.get("timestep"),
            "climate_zone": parameter_dict.get("climate_zone"),
        }
    result: dict[str, Any] = {
        "target": target,
        "uwg_json_artifact_target": target,
        "summary_view": summary_view,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=UWG_JSON_ARTIFACT_TYPE,
            artifact_path=target["path"],
            absolute_path=str(output_path),
            source={
                "model_target": resolved_model_target,
                "weather_target": weather_target or {},
                "simulation_parameter_target": parameter_target or {},
            },
        ),
        "report": make_report(status="ok", message=f"Wrote UWG JSON artifact: {identifier}"),
    }
    if include_body:
        result["object_dict"] = uwg_dict
    return result


def resolve_epw_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
) -> Path:
    """Resolve an exact Garden weather_file target to its EPW path."""
    if weather_target is None:
        raise ValueError("weather_target is required.")
    if not isinstance(weather_target, dict):
        raise ValueError("weather_target must be a dictionary.")
    if weather_target.get("target_type") != "weather_file":
        raise ValueError("weather_target must be a Garden weather_file target.")
    if weather_target.get("garden_id") != manifest.garden_id:
        raise ValueError("weather_target belongs to a different Garden.")
    path_value = weather_target.get("epw_path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("weather_target requires epw_path.")
    if Path(path_value).is_absolute():
        raise ValueError("weather_target epw_path must be Garden-relative.")
    return resolve_existing_garden_path(
        garden_root, path_value, kind="file", suffix=".epw", label="UWG weather input"
    )


def make_uwg_json_artifact_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a UWG JSON artifact target."""
    return {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": UWG_DOMAIN,
        "artifact_type": UWG_JSON_ARTIFACT_TYPE,
        "identifier": identifier,
        "path": path,
    }


# ---------------------------------------------------------------------------
# UWG simulation runs & ledger
# ---------------------------------------------------------------------------


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


def _record_worker_pid(garden_root: Path, run_id: str, proc: Any) -> None:
    worker_pid = getattr(proc, "pid", None)
    if worker_pid is None:
        return
    current = _UWG_RUNS.get(garden_root, run_id)
    if current is not None and current.get("worker_pid") is None:
        current["worker_pid"] = worker_pid
        _UWG_RUNS.upsert(garden_root, current)


def _run_uwg_worker(**kwargs: Any) -> None:
    garden_root_path = require_garden_root(kwargs["garden_root"])
    run_id = str(kwargs["run_id"])
    current = _UWG_RUNS.get(garden_root_path, run_id)
    if current is not None and current.get("worker_pid") is None:
        current["worker_pid"] = os.getpid()
        _UWG_RUNS.upsert(garden_root_path, current)
    run_uwg(**kwargs)
    latest = _UWG_RUNS.get(garden_root_path, run_id)
    if latest is not None and latest.get("worker_pid") is None:
        latest["worker_pid"] = os.getpid()
        _UWG_RUNS.upsert(garden_root_path, latest)


def _compute_uhi_summary(rural_epw_path: Path, urban_epw_path: Path) -> dict[str, Any] | None:
    try:
        rural = EPW(str(rural_epw_path))
        urban = EPW(str(urban_epw_path))
        rural_temps = [float(t) for t in rural.dry_bulb_temperature.values]
        urban_temps = [float(t) for t in urban.dry_bulb_temperature.values]
        if not rural_temps or len(rural_temps) != len(urban_temps):
            return None
        deltas = [u - r for u, r in zip(urban_temps, rural_temps, strict=True)]
        rural_hdd = sum(max(18.3 - t, 0.0) for t in rural_temps) / 24.0
        urban_hdd = sum(max(18.3 - t, 0.0) for t in urban_temps) / 24.0
        rural_cdd_10 = sum(max(t - 10.0, 0.0) for t in rural_temps) / 24.0
        urban_cdd_10 = sum(max(t - 10.0, 0.0) for t in urban_temps) / 24.0
        rural_cdd_18 = sum(max(t - 18.3, 0.0) for t in rural_temps) / 24.0
        urban_cdd_18 = sum(max(t - 18.3, 0.0) for t in urban_temps) / 24.0
        mean_rural = sum(rural_temps) / len(rural_temps)
        mean_urban = sum(urban_temps) / len(urban_temps)
        return {
            "hour_count": len(rural_temps),
            "mean_rural_dry_bulb_c": round(mean_rural, 3),
            "mean_urban_dry_bulb_c": round(mean_urban, 3),
            "mean_uhi_delta_c": round(sum(deltas) / len(deltas), 3),
            "max_uhi_delta_c": round(max(deltas), 3),
            "min_uhi_delta_c": round(min(deltas), 3),
            "rural_hdd_18_3c": round(rural_hdd, 2),
            "urban_hdd_18_3c": round(urban_hdd, 2),
            "hdd_18_3c_delta": round(urban_hdd - rural_hdd, 2),
            "rural_cdd_10c": round(rural_cdd_10, 2),
            "urban_cdd_10c": round(urban_cdd_10, 2),
            "cdd_10c_delta": round(urban_cdd_10 - rural_cdd_10, 2),
            "rural_cdd_18_3c": round(rural_cdd_18, 2),
            "urban_cdd_18_3c": round(urban_cdd_18, 2),
            "cdd_18_3c_delta": round(urban_cdd_18 - rural_cdd_18, 2),
        }
    except Exception:
        return None


def run_uwg(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    run_id: str | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
) -> dict[str, Any]:
    """Run UWG synchronously and register the morphed EPW as a weather target."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_run_id = _normalize_run_id(run_id, resolved_model_target)
    existing = _UWG_RUNS.get(garden_root_path, normalized_run_id)
    if reload_old and existing and existing.get("status") == "completed":
        return _result_from_record(
            existing,
            "Reloaded completed UWG run.",
            garden_root=str(garden_root_path),
        )

    target = _UWG_RUNS.make_target(manifest.garden_id, normalized_run_id)
    run_dir = _UWG_RUNS.run_dir(garden_root_path, normalized_run_id)
    outputs_dir = run_dir / "outputs"
    inputs_dir = run_dir / "inputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    stdio_log = run_dir / "uwg_stdio.log"
    started_at = utc_now_iso()

    try:
        model = load_dragonfly_model(garden_root_path, resolved_model_target)
        resolved_epw = resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        preflight = (
            _preflight_epw(resolved_epw)
            if validate_weather
            else {"status": "skipped", "issues": []}
        )
        if preflight["status"] == "failed":
            raise ValueError("; ".join(preflight["issues"]))
        parameter, parameter_target, parameter_dict = load_uwg_simulation_parameter(
            garden_root=garden_root_path,
            simulation_parameter_target=simulation_parameter_target,
            simulation_parameter=simulation_parameter,
        )
        if parameter_dict is not None:
            (inputs_dir / "simulation_parameter.json").write_text(
                json.dumps(parameter_dict, indent=2) + "\n",
                encoding="utf-8",
            )
        uwg_json_path, morphed_epw_path = _run_uwg_cli(
            model=model,
            epw_file_path=resolved_epw,
            simulation_parameter=parameter,
            directory=outputs_dir,
            stdio_log=stdio_log,
            timeout_seconds=UWG_CLI_TIMEOUT_SECONDS,
        )
        weather = _register_morphed_weather_target(
            garden_root=garden_root_path,
            manifest=manifest,
            run_target=target,
            run_id=normalized_run_id,
            epw_path=morphed_epw_path,
            source_weather_target=weather_target,
        )
        uhi_summary = _compute_uhi_summary(resolved_epw, morphed_epw_path)
        latest_existing = _UWG_RUNS.get(garden_root_path, normalized_run_id)
        outputs_payload: dict[str, Any] = {
            "uwg_json": _output("uwg_json", garden_root_path, uwg_json_path),
            "morphed_epw": _output("morphed_epw", garden_root_path, morphed_epw_path),
            "weather_target": weather,
            "stdio_log": _output("stdio_log", garden_root_path, stdio_log),
        }
        if uhi_summary is not None:
            outputs_payload["uhi_summary"] = uhi_summary
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="completed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=utc_now_iso(),
            preflight=preflight,
            worker_pid=(latest_existing or {}).get("worker_pid"),
            outputs=outputs_payload,
        )
    except Exception as exc:
        traceback_text = traceback.format_exc()
        stdio_log.parent.mkdir(parents=True, exist_ok=True)
        with stdio_log.open("a", encoding="utf-8") as handle:
            handle.write(traceback_text)
        latest_existing = _UWG_RUNS.get(garden_root_path, normalized_run_id)
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="failed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=utc_now_iso(),
            preflight={"status": "failed", "issues": [str(exc)]},
            error=str(exc),
            worker_pid=(latest_existing or {}).get("worker_pid"),
            outputs={"stdio_log": _output("stdio_log", garden_root_path, stdio_log)},
        )
    _UWG_RUNS.upsert(garden_root_path, record)
    return _result_from_record(
        record,
        f"UWG run {record['status']}: {normalized_run_id}",
        garden_root=str(garden_root_path),
    )


def start_uwg_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    run_id: str | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start UWG in the background and return a run target."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_run_id = _normalize_run_id(run_id, resolved_model_target)
    existing = _UWG_RUNS.get(garden_root_path, normalized_run_id)
    if reload_old and existing and existing.get("status") == "completed":
        return _result_from_record(
            existing,
            "Reloaded completed UWG run.",
            garden_root=str(garden_root_path),
        )

    target = _UWG_RUNS.make_target(manifest.garden_id, normalized_run_id)
    run_dir = _UWG_RUNS.run_dir(garden_root_path, normalized_run_id)
    started_at = utc_now_iso()
    try:
        resolved_epw = resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        preflight = (
            _preflight_epw(resolved_epw)
            if validate_weather
            else {"status": "skipped", "issues": []}
        )
    except Exception as exc:
        preflight = {"status": "failed", "issues": [str(exc)]}

    if preflight["status"] == "failed":
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="failed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=utc_now_iso(),
            preflight=preflight,
            error="; ".join(preflight["issues"]),
            outputs={},
        )
        _UWG_RUNS.upsert(garden_root_path, record)
        return _result_from_record(
            record,
            f"UWG preflight failed: {normalized_run_id}",
            garden_root=str(garden_root_path),
        )

    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        status="running",
        model_target=resolved_model_target,
        weather_target=weather_target,
        simulation_parameter_target=simulation_parameter_target,
        run_dir=run_dir,
        started_at=started_at,
        preflight=preflight,
        outputs={},
    )
    _UWG_RUNS.upsert(garden_root_path, record)
    try:
        proc = submit_worker_process(
            garden_root=garden_root_path,
            run_dir=run_dir,
            worker_module="garden.run_uwg:_run_uwg_worker",
            request=_json_safe(
                {
                    "garden_root": str(garden_root_path),
                    "model_target": resolved_model_target,
                    "weather_target": weather_target,
                    "simulation_parameter_target": simulation_parameter_target,
                    "simulation_parameter": simulation_parameter,
                    "run_id": normalized_run_id,
                    "reload_old": False,
                    "silent": silent,
                    "validate_weather": False,
                }
            ),
            cwd=garden_root_path,
            environment=_worker_environment(garden_root_path, run_dir),
        )
        _record_worker_pid(garden_root_path, normalized_run_id, proc)
    except Exception as exc:
        record.update(_UWG_RUNS.failure_fields(str(exc), traceback.format_exc()))
        _UWG_RUNS.upsert(garden_root_path, record)
        return _result_from_record(
            record,
            f"UWG run failed to start: {normalized_run_id}",
            garden_root=str(garden_root_path),
        )

    latest = _UWG_RUNS.get(garden_root_path, normalized_run_id) or record
    requested_wait = max(float(wait_seconds or 0), 0.0)
    if not requested_wait:
        return _result_from_record(
            latest,
            f"UWG run started: {normalized_run_id}",
            garden_root=str(garden_root_path),
        )
    applied_wait = min(requested_wait, 3500.0)
    interval = max(float(poll_interval or 2.0), 0.2)
    deadline = time.monotonic() + applied_wait
    while latest.get("status") in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
        latest = _UWG_RUNS.get(garden_root_path, normalized_run_id) or latest
    result = _result_from_record(
        latest,
        f"UWG run {latest['status']}: {normalized_run_id}",
        garden_root=str(garden_root_path),
    )
    summary_view = result.setdefault("summary_view", {})
    summary_view["wait_seconds_requested"] = wait_seconds
    summary_view["wait_seconds_applied"] = applied_wait
    return result


def get_uwg_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return a UWG run record."""
    garden_root_path = require_garden_root(garden_root)
    resolved_id = _UWG_RUNS.resolve_run_id(run_target, run_id)
    record = _UWG_RUNS.require(garden_root_path, resolved_id)
    return {
        "target": record["target"],
        "uwg_run_target": record["target"],
        "summary_view": {"run": _public_run(record)},
        "report": make_report(status="ok", message=f"Read UWG run: {resolved_id}"),
    }


def list_uwg_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List UWG run records."""
    garden_root_path = require_garden_root(garden_root)
    records = _UWG_RUNS.list(garden_root_path)
    if status is not None:
        records = [record for record in records if record.get("status") == status]
    matches = [_public_run(record) for record in records]
    return {
        "matches": matches,
        "summary_view": {"count": len(matches), "status": status},
        "report": make_report(status="ok", message=f"Found {len(matches)} UWG run(s)."),
    }


def list_uwg_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List UWG run outputs."""
    garden_root_path = require_garden_root(garden_root)
    resolved_id = _UWG_RUNS.resolve_run_id(run_target, run_id)
    record = _UWG_RUNS.require(garden_root_path, resolved_id)
    outputs = record.get("outputs") or {}
    matches = []
    for name in OUTPUT_NAMES:
        value = outputs.get(name)
        if value is None:
            continue
        if isinstance(value, dict) and value.get("target_type") == "weather_file":
            matches.append({"name": name, "target": value, "exists": True})
        else:
            matches.append(value)
    return {
        "matches": matches,
        "summary_view": {"run_id": resolved_id, "count": len(matches), "outputs": outputs},
        "report": make_report(status="ok", message=f"Listed UWG outputs: {resolved_id}"),
    }


def _run_uwg_cli(
    *,
    model: Any,
    epw_file_path: Path,
    simulation_parameter: Any,
    directory: Path,
    stdio_log: Path,
    timeout_seconds: int,
) -> tuple[Path, Path]:
    """Write UWG JSON and run the UWG CLI with bounded, captured stdio."""
    directory.mkdir(parents=True, exist_ok=True)
    stdio_log.parent.mkdir(parents=True, exist_ok=True)
    uwg_json_path = directory / f"{model.identifier}_uwg.json"
    morphed_epw_path = directory / f"{model.identifier}.epw"
    uwg_dict = sdk_model_to_uwg(model, str(epw_file_path), simulation_parameter=simulation_parameter)
    uwg_json_path.write_text(json.dumps(uwg_dict, indent=4) + "\n", encoding="utf-8")
    python_exe = str(hb_folders.python_exe_path or sys.executable)
    cmd = [
        python_exe,
        "-m",
        "uwg",
        "simulate",
        "model",
        str(uwg_json_path),
        str(epw_file_path),
        "--new-epw-dir",
        str(directory),
        "--new-epw-name",
        morphed_epw_path.name,
    ]
    env = os.environ.copy()
    env["PYTHONHOME"] = ""
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(directory),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _write_uwg_stdio_log(stdio_log, cmd, exc.stdout, exc.stderr)
        raise RuntimeError(f"UWG CLI timed out after {timeout_seconds} seconds.") from exc
    _write_uwg_stdio_log(stdio_log, cmd, completed.stdout, completed.stderr)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"The UWG failed to run:\n{message}")
    if not morphed_epw_path.is_file():
        raise RuntimeError(f"UWG did not produce morphed EPW: {morphed_epw_path}")
    return uwg_json_path, morphed_epw_path


def _write_uwg_stdio_log(
    path: Path,
    cmd: list[str],
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> None:
    def _text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value

    path.write_text(
        "command: " + " ".join(cmd) + "\n\n[stdout]\n" + _text(stdout) + "\n[stderr]\n" + _text(stderr),
        encoding="utf-8",
    )


def _normalize_run_id(run_id: str | None, model_target: dict[str, Any]) -> str:
    return _UWG_RUNS.normalize_run_id(
        run_id,
        fallback=run_id or f"{model_target['model_identifier']}_uwg_{uuid4().hex[:8]}",
    )


def _record(
    *,
    garden_root: Path,
    run_id: str,
    target: dict[str, Any],
    status: str,
    model_target: dict[str, Any],
    weather_target: dict[str, Any] | None,
    simulation_parameter_target: dict[str, Any] | None,
    run_dir: Path,
    started_at: str,
    completed_at: str | None = None,
    preflight: dict[str, Any] | None = None,
    error: str | None = None,
    worker_pid: int | None = None,
    outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "run_id": run_id,
        "target": target,
        "recipe": UWG_RUN_RECIPE,
        "status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "model_target": model_target,
        "weather_target": weather_target or {},
        "simulation_parameter_target": simulation_parameter_target or {},
        "preflight": preflight or {"status": "skipped", "issues": []},
        "outputs": outputs or {},
    }
    if worker_pid is not None:
        record["worker_pid"] = worker_pid
    if completed_at is not None:
        record["completed_at"] = completed_at
    if error:
        record["error"] = error
    return record


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    public = _UWG_RUNS.public_run(record)
    public["outputs"] = record.get("outputs") or {}
    return public


def _result_from_record(
    record: dict[str, Any],
    message: str,
    *,
    garden_root: str | None = None,
) -> dict[str, Any]:
    target = record["target"]
    poll_next = {
        "tool": "GD_Poll_Run",
        "arguments": {"garden_root": garden_root, "run_target": target},
    }
    outputs = record.get("outputs") or {}
    summary_view: dict[str, Any] = {
        "status": record["status"],
        "run": _public_run(record),
        "outputs": outputs,
        "poll_next": poll_next,
    }
    if isinstance(outputs.get("uhi_summary"), dict):
        summary_view["uhi_summary"] = outputs["uhi_summary"]
    result: dict[str, Any] = {
        "target": target,
        "uwg_run_target": target,
        "run_target": target,
        "runtime_status": record["status"],
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status="failed" if record.get("status") == "failed" else "ok",
            message=message,
        ),
    }
    if record.get("worker_pid") is not None:
        summary_view["worker_pid"] = record["worker_pid"]
        result["worker_pid"] = record["worker_pid"]
    return result


def _preflight_epw(path: Path) -> dict[str, Any]:
    try:
        epw = EPW(str(path))
        if len(epw.dry_bulb_temperature.values) != 8760:
            raise ValueError("EPW dry-bulb temperature series is not 8760 hours.")
    except Exception as exc:
        return {"status": "failed", "issues": [f"Invalid EPW: {exc}"]}
    return {"status": "ok", "issues": []}


def _register_morphed_weather_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_target: dict[str, Any],
    run_id: str,
    epw_path: Path,
    source_weather_target: dict[str, Any] | None,
) -> dict[str, Any]:
    ddy_path = None
    stat_path = None
    if source_weather_target:
        if source_weather_target.get("ddy_path"):
            candidate = garden_root / str(source_weather_target["ddy_path"])
            ddy_path = candidate.resolve() if candidate.exists() else None
        if source_weather_target.get("stat_path"):
            candidate = garden_root / str(source_weather_target["stat_path"])
            stat_path = candidate.resolve() if candidate.exists() else None
    target = make_garden_weather_target(
        garden_root=garden_root,
        manifest=manifest,
        identifier=f"{run_id}_uwg_weather",
        epw_path=epw_path,
        ddy_path=ddy_path,
        stat_path=stat_path,
        metadata={
            "source": "uwg",
            "source_run_target": run_target,
            "search_terms": ["uwg", "urban", "morphed", run_id],
        },
    )
    manifest.weather_files = [
        item for item in manifest.weather_files if item.get("identifier") != target["identifier"]
    ]
    manifest.weather_files.append(target)
    manifest.write(garden_root)
    return target


def _output(name: str, garden_root: Path, path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "path": to_posix_relative(path, garden_root),
        "exists": path.exists(),
    }


__all__ = [
    "UWG_ARTIFACT_DIR",
    "UWG_DOMAIN",
    "UWG_JSON_ARTIFACT_TYPE",
    "UWG_PARAMETER_TARGET_TYPE",
    "UWG_RUN_RECIPE",
    "UWG_RUN_TARGET_TYPE",
    "create_uwg_simulation_parameter",
    "dragonfly_model_to_uwg",
    "get_uwg_run",
    "list_uwg_run_outputs",
    "list_uwg_runs",
    "load_uwg_simulation_parameter",
    "make_uwg_json_artifact_target",
    "make_uwg_simulation_parameter_target",
    "normalize_uwg_simulation_parameter_target",
    "resolve_epw_path",
    "run_uwg",
    "start_uwg_run",
]
