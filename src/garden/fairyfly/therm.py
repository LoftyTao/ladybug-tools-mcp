"""Fairyfly THERM targets, writing, run ledger, and result parsing services."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from statistics import fmean
import time
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from fairyfly_next_therm.result import THMZResult
from fairyfly_next_therm.run import run_thmz
from fairyfly_next_therm.simulation.exposure import ModelExposure
from fairyfly_next_therm.simulation.mesh import MeshControl
from fairyfly_next_therm.simulation.parameter import SimulationParameter
from fairyfly_next_therm.simulation.transient import TransientCalculation
from fairyfly_next_therm.writer import model_to_thmz
from ladybug.psychrometrics import dew_point_from_db_rh, rel_humid_from_db_dpt
from ladybug_geometry.geometry2d.pointvector import Point2D
from pyhygrothermfem_fairyfly.transient_results import (
    TRANSIENT_RESULT_MEMBERS,
    TRANSIENT_STEP_EXCHANGE_MEMBERS,
    read_geometry_xml,
    read_transient_series,
)

from garden.background import submit_worker_process
from garden.fairyfly.availability import therm_engine_config
from garden.fairyfly.mesher import gmsh_mesh_to_xml, mesh_thmz_in_place, thmz_has_mesh
from garden.fairyfly.model import load_fairyfly_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_ledger import RunLedger, RunManager
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

FAIRYFLY_THERM_RECIPE = "therm"
FAIRYFLY_THMZ_TARGET_TYPE = "fairyfly_thmz"
FAIRYFLY_THERM_RUN_TARGET_TYPE = "fairyfly_therm_run"
FAIRYFLY_THERM_RESULT_TARGET_TYPE = "fairyfly_therm_result"
FAIRYFLY_THERM_DOMAIN = "fairyfly"
FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE = "fairyfly_therm_result"

FAIRYFLY_THERM_RUNS_DIR = Path("runs") / "fairyfly_therm"
FAIRYFLY_THERM_INDEX = FAIRYFLY_THERM_RUNS_DIR / "index.json"
RESULTS_DIR = Path("artifacts") / "fairyfly" / "results"

_DATA_TYPE_ATTRS = {
    "temperature": "temperatures",
    "temperatures": "temperatures",
    "heat_flux": "heat_flux_magnitudes",
    "heat_flux_magnitude": "heat_flux_magnitudes",
    "heat_flux_magnitudes": "heat_flux_magnitudes",
    "heat_flux_vector": "heat_fluxes",
    "heat_flux_vectors": "heat_fluxes",
    "heat_fluxes": "heat_fluxes",
    "humidity": "humidities",
    "humidities": "humidities",
    "relative_humidity": "humidities",
    "water_content": "water_contents",
    "water_contents": "water_contents",
    "moisture_content": "water_contents",
}
_DATA_TYPE_NAMES = {
    "temperatures": "temperature",
    "heat_flux_magnitudes": "heat_flux",
    "heat_fluxes": "heat_flux_vectors",
    "humidities": "humidity",
    "water_contents": "water_content",
}
_TRANSIENT_NODE_FIELD_MAP = {
    "temperature": TRANSIENT_RESULT_MEMBERS["temperatures"],
    "heat_flux": TRANSIENT_RESULT_MEMBERS["heat_flux"],
    "humidity": TRANSIENT_RESULT_MEMBERS["humidities"],
    "water_content": TRANSIENT_RESULT_MEMBERS["water_content"],
}
_TRANSIENT_SERIES_FIELDS = (
    ("temperatures", TRANSIENT_RESULT_MEMBERS["temperatures"]),
    ("humidities", TRANSIENT_RESULT_MEMBERS["humidities"]),
    ("water_content", TRANSIENT_RESULT_MEMBERS["water_content"]),
    ("heat_flux", TRANSIENT_RESULT_MEMBERS["heat_flux"]),
    ("water_flux", TRANSIENT_RESULT_MEMBERS["water_flux"]),
    ("heat_flux_edges", TRANSIENT_RESULT_MEMBERS["heat_flux_edges"]),
    ("water_flux_edges", TRANSIENT_RESULT_MEMBERS["water_flux_edges"]),
    ("heat_flux_step_exchange", TRANSIENT_STEP_EXCHANGE_MEMBERS["heat_flux_step_exchange"]),
    ("water_flux_step_exchange", TRANSIENT_STEP_EXCHANGE_MEMBERS["water_flux_step_exchange"]),
)
_TRANSIENT_FIELD_ALIASES = {
    **{k: (k, v) for k, v in _TRANSIENT_SERIES_FIELDS},
    "temperature": ("temperatures", TRANSIENT_RESULT_MEMBERS["temperatures"]),
    "humidity": ("humidities", TRANSIENT_RESULT_MEMBERS["humidities"]),
    "water_contents": ("water_content", TRANSIENT_RESULT_MEMBERS["water_content"]),
    "moisture_content": ("water_content", TRANSIENT_RESULT_MEMBERS["water_content"]),
}
_U_FACTOR_FIELDS = (
    "name",
    "delta_temperature",
    "heat_flux",
    "total_u_factor",
    "total_length",
    "projected_x_u_factor",
    "projected_x_length",
    "projected_y_u_factor",
    "projected_y_length",
    "projected_in_glass_plane_u_factor",
    "projected_in_glass_plane_length",
    "custom_rotation_u_factor",
    "custom_rotation_length",
)
_LENGTH_TO_METERS = {
    "meters": 1.0,
    "meter": 1.0,
    "m": 1.0,
    "millimeters": 0.001,
    "millimeter": 0.001,
    "mm": 0.001,
    "centimeters": 0.01,
    "centimeter": 0.01,
    "cm": 0.01,
    "feet": 0.3048,
    "foot": 0.3048,
    "ft": 0.3048,
    "inches": 0.0254,
    "inch": 0.0254,
    "in": 0.0254,
}

_THERM_RUNS = RunManager(
    domain=FAIRYFLY_THERM_DOMAIN,
    target_type=FAIRYFLY_THERM_RUN_TARGET_TYPE,
    runs_dir=FAIRYFLY_THERM_RUNS_DIR,
    default_recipe=FAIRYFLY_THERM_RECIPE,
    allowed_recipes={FAIRYFLY_THERM_RECIPE},
    run_id_prefix="fairyfly_therm",
    missing_message="Provide run_target or run_id.",
    not_found_label="Fairyfly THERM",
    public_fields=(
        "run_id",
        "target",
        "recipe",
        "status",
        "runtime_status",
        "worker_pid",
        "error",
        "created_at",
        "completed_at",
        "model_target",
        "model_path",
        "run_folder",
        "thmz_target",
        "thmz_path",
        "simulation_parameter",
        "simulation_mode",
        "solver_provenance",
        "mesh_convergence",
        "source_thmz_path",
        "engine",
        "disabled_reason",
        "warnings",
    ),
    ledger=RunLedger(lock="file", atomic=True, recover_trailing_json=True, sort_by_created_at=True),
)


def make_fairyfly_thmz_target(garden_id: str, run_id: str, path: str) -> dict[str, Any]:
    """Build a Fairyfly THERM THMZ artifact target."""
    return {
        "target_type": FAIRYFLY_THMZ_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "path": path,
    }


def make_fairyfly_therm_run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    """Build a Fairyfly THERM run target."""
    return _THERM_RUNS.make_target(garden_id, run_id)


def make_fairyfly_therm_result_target(
    garden_id: str,
    run_id: str,
    data_type: str,
    path: str,
) -> dict[str, Any]:
    """Build a Fairyfly THERM result target."""
    return {
        "target_type": FAIRYFLY_THERM_RESULT_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "data_type": data_type,
        "path": path,
    }


def make_fairyfly_u_factor_result_target(garden_id: str, run_id: str, path: str) -> dict[str, Any]:
    """Build the U-Factor specialization of a Fairyfly THERM result target."""
    return make_fairyfly_therm_result_target(
        garden_id=garden_id,
        run_id=run_id,
        data_type="u_factors",
        path=path,
    )


def normalize_fairyfly_therm_run_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Fairyfly THERM run target."""
    if not isinstance(value, dict):
        raise ValueError("Fairyfly THERM run target must be a dictionary.")
    if value.get("target_type") != FAIRYFLY_THERM_RUN_TARGET_TYPE:
        raise ValueError("run_target must have target_type 'fairyfly_therm_run'.")
    if value.get("domain") != FAIRYFLY_THERM_DOMAIN:
        raise ValueError("run_target must reference domain 'fairyfly'.")
    if value.get("recipe") != FAIRYFLY_THERM_RECIPE:
        raise ValueError("run_target must reference recipe 'therm'.")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_target requires run_id.")
    return dict(value)


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    return manifest.upsert_artifact(
        {
            "artifact_type": artifact_type,
            "name": name,
            "path": path,
            "source": source,
            "created_at": utc_now_iso(),
        }
    )


def _coerce_simulation_parameter(
    simulation_parameter: SimulationParameter | dict[str, Any] | None,
) -> SimulationParameter | None:
    """Coerce a dict spec or SimulationParameter into a fairyfly_therm SimulationParameter."""
    if simulation_parameter is None:
        return None
    if isinstance(simulation_parameter, SimulationParameter):
        return simulation_parameter
    if not isinstance(simulation_parameter, dict):
        raise ValueError("simulation_parameter must be a dictionary.")
    if isinstance(simulation_parameter.get("object_dict"), dict):
        simulation_parameter = simulation_parameter["object_dict"]
    if simulation_parameter.get("type") == "SimulationParameter":
        return SimulationParameter.from_dict(simulation_parameter)

    mesh_ctrl: MeshControl | None = None
    mesh_raw = simulation_parameter.get("mesh")
    if isinstance(mesh_raw, dict):
        mesh_ctrl = (
            MeshControl.from_dict(mesh_raw)
            if mesh_raw.get("type") == "MeshControl"
            else MeshControl(
                mesh_type=str(mesh_raw.get("mesh_type", "Simmetrix")),
                parameter=int(mesh_raw.get("parameter", 20)),
                run_error_estimator=bool(mesh_raw.get("run_error_estimator", True)),
                max_error_percent=float(mesh_raw.get("max_error_percent", 10.0)),
                max_iterations=int(mesh_raw.get("max_iterations", 5)),
            )
        )

    exposure_obj: ModelExposure | None = None
    exposure_raw = simulation_parameter.get("exposure")
    if isinstance(exposure_raw, dict):
        exposure_obj = (
            ModelExposure.from_dict(exposure_raw)
            if exposure_raw.get("type") == "ModelExposure"
            else ModelExposure(
                model_type=str(exposure_raw.get("model_type", "Other")),
                cross_section_type=exposure_raw.get("cross_section_type"),
                gravity_orientation=exposure_raw.get("gravity_orientation"),
                wind_orientation=float(exposure_raw.get("wind_orientation", 0.0)),
            )
        )

    transient_obj: TransientCalculation | None = None
    transient_raw = simulation_parameter.get("transient")
    if isinstance(transient_raw, dict):
        if transient_raw.get("type") == "TransientCalculation":
            transient_obj = TransientCalculation.from_dict(transient_raw)
        else:
            t_kwargs: dict[str, Any] = {}
            for key in (
                "time_range",
                "timestep",
                "number_of_timesteps",
                "initial_temperature",
                "initial_humidity",
                "methodology",
                "simulate_moisture",
                "convergence_tolerance",
                "relaxation_parameter",
                "modeling_options",
            ):
                if transient_raw.get(key) is not None:
                    t_kwargs[key] = transient_raw[key]
            transient_obj = TransientCalculation(**t_kwargs)

    return SimulationParameter(mesh=mesh_ctrl, exposure=exposure_obj, transient=transient_obj)


def _run_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
    report_status: str = "ok",
) -> dict[str, Any]:
    target = record["target"]
    summary = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "status": record["status"],
        "runtime_status": record.get("runtime_status") or record["status"],
        "worker_pid": record.get("worker_pid"),
        "error": record.get("error"),
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_folder": record.get("run_folder"),
        "thmz_target": record.get("thmz_target"),
        "simulation_parameter": record.get("simulation_parameter"),
        "simulation_mode": record.get("simulation_mode"),
        "solver_provenance": record.get("solver_provenance"),
        "mesh_convergence": record.get("mesh_convergence"),
        "source_thmz_path": record.get("source_thmz_path"),
        "engine": record.get("engine"),
        "disabled_reason": record.get("disabled_reason"),
        "poll_next": {
            "tool": "GD_Poll_Run",
            "arguments": {"garden_root": str(garden_root), "run_target": target},
        },
    }
    return {
        "target": target,
        "run_target": target,
        "fairyfly_therm_run_target": target,
        "run_id": record["run_id"],
        "status": record["status"],
        "runtime_status": record.get("runtime_status") or record["status"],
        "worker_pid": record.get("worker_pid"),
        "error": record.get("error"),
        "summary_view": summary,
        "report": make_report(
            status=report_status,
            message=message,
            warnings=list(record.get("warnings", [])),
        ),
    }


def write_fairyfly_model_to_thmz(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    name: str | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    include_mesh: bool = False,
) -> dict[str, Any]:
    """Write a Garden-backed Fairyfly model to a THERM THMZ artifact."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    sim_par = _coerce_simulation_parameter(simulation_parameter)
    normalized_run_id = _THERM_RUNS.normalize_run_id(run_id)
    run_dir = _THERM_RUNS.run_dir(garden_root_path, normalized_run_id)
    safe_name = slugify_name(name) if name else "model"
    thmz_path = run_dir / f"{safe_name}.thmz"
    model_to_thmz(
        model,
        str(thmz_path),
        sim_par,
        mesh_generator=gmsh_mesh_to_xml if include_mesh else None,
    )
    has_mesh = thmz_has_mesh(thmz_path)
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    target = make_fairyfly_thmz_target(
        garden_id=manifest.garden_id,
        run_id=normalized_run_id,
        path=thmz_relative_path,
    )
    model_path = resolved_model_target.get("path")
    source = {
        "run_id": normalized_run_id,
        "model_target": resolved_model_target,
        "model_path": model_path,
        "include_mesh": bool(include_mesh),
    }
    artifact = _register_artifact(
        manifest,
        artifact_type="fairyfly_thmz",
        name=f"{normalized_run_id}_{safe_name}",
        path=thmz_relative_path,
        source=source,
    )
    manifest.write(garden_root_path)
    return {
        "target": target,
        "thmz_target": target,
        "model_target": resolved_model_target,
        "artifact": artifact,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type="fairyfly_thmz",
            artifact_path=thmz_relative_path,
            absolute_path=str(thmz_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": normalized_run_id,
            "status": "written",
            "path": thmz_relative_path,
            "include_mesh": bool(include_mesh),
            "has_mesh": has_mesh,
            "model_target": resolved_model_target,
            "model_path": model_path,
            "simulation_parameter": sim_par.to_dict() if sim_par is not None else None,
            "artifact": artifact,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly model written to THERM THMZ: {thmz_relative_path}",
        ),
    }


def _verify_solver_outputs(thmz_path: Path) -> dict[str, Any]:
    """Verify pyHygroTherm.json provenance inside a solved THMZ archive."""
    if not thmz_path.is_file():
        raise RuntimeError(f"Solver output THMZ not found: {thmz_path}")
    with zipfile.ZipFile(thmz_path, "r") as archive:
        try:
            raw = archive.read("pyHygroTherm.json")
        except KeyError as exc:
            raise RuntimeError(
                f"pyHygroThermFEM simulation did not write pyHygroTherm.json in {thmz_path}."
            ) from exc
    provenance = json.loads(raw.decode("utf-8"))
    if not isinstance(provenance, dict) or not provenance.get("contract_version"):
        raise RuntimeError("Solved THMZ pyHygroTherm.json is missing contract_version.")
    mode = provenance.get("mode")
    if mode not in {"dry-steady", "dry-transient", "hygrothermal-transient"}:
        raise RuntimeError(f"Unsupported solver provenance mode {mode!r} in pyHygroTherm.json.")
    return provenance


def _run_therm_worker(
    *,
    garden_root: str,
    run_id: str,
    garden_id: str,
    model_target: dict[str, Any] | None = None,
    thmz_source_path: str | None = None,
    silent: bool = True,
    simulation_parameter: dict[str, Any] | None = None,
) -> None:
    """Background worker that meshes (via Gmsh), runs pyHygroThermFEM, and verifies provenance."""
    garden_root_path = Path(garden_root).resolve()
    run_dir = _THERM_RUNS.run_dir(garden_root_path, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    thmz_path = run_dir / "model.thmz"
    existing = _THERM_RUNS.require(garden_root_path, run_id)
    warnings: list[str] = list(existing.get("warnings", []))
    error: str | None = None
    status = "completed"
    provenance: dict[str, Any] | None = None
    mesh_convergence: dict[str, Any] | None = None

    try:
        sim_par = _coerce_simulation_parameter(simulation_parameter)
        if thmz_source_path:
            source_file = Path(thmz_source_path)
            if not source_file.is_file():
                raise ValueError(f"Source THMZ file not found: {source_file}")
            shutil.copy2(source_file, thmz_path)
            premeshed = thmz_has_mesh(thmz_path)
            if not premeshed:
                target_quad = max(int(sim_par.mesh.parameter), 4) if sim_par is not None else 20
                mesh_thmz_in_place(thmz_path, target_quad_count=target_quad)
            run_thmz(str(thmz_path), silent=silent)
            provenance = _verify_solver_outputs(thmz_path)
            mesh_convergence = {
                "premeshed": premeshed,
                "converged": True,
                "energy_error_percent": provenance.get("energy_error_percent"),
            }
        else:
            if model_target is None:
                raise ValueError("model_target is required when thmz_target/thmz_path is omitted.")
            model = load_fairyfly_model(garden_root_path, model_target)
            effective_par = sim_par if sim_par is not None else SimulationParameter()
            control = effective_par.mesh
            if effective_par.transient is None and control.run_error_estimator:
                target = max(int(control.parameter), 4)
                max_iterations = max(int(control.max_iterations), 1)
                max_error_percent = float(control.max_error_percent)
                converged = False
                energy_error: float | None = None
                attempts_used = 0
                for attempt in range(1, max_iterations + 1):
                    attempts_used = attempt
                    step_par = effective_par.duplicate()
                    step_par.mesh.parameter = target
                    model_to_thmz(
                        model,
                        str(thmz_path),
                        step_par,
                        mesh_generator=gmsh_mesh_to_xml,
                    )
                    run_thmz(str(thmz_path), silent=silent)
                    provenance = _verify_solver_outputs(thmz_path)
                    raw_err = provenance.get("energy_error_percent")
                    energy_error = float(raw_err) if raw_err is not None else None
                    if energy_error is None or energy_error <= max_error_percent:
                        converged = True
                        break
                    if attempt < max_iterations:
                        target = min(target * 4, 200000)
                if not converged and energy_error is not None:
                    warnings.append(
                        f"Steady-state energy error {energy_error:.3f}% exceeded max_error_percent "
                        f"{max_error_percent:.3f}% after {attempts_used} iteration(s)."
                    )
                mesh_convergence = {
                    "premeshed": False,
                    "converged": converged,
                    "iterations": attempts_used,
                    "final_target_quad_count": target,
                    "energy_error_percent": energy_error,
                    "max_error_percent": max_error_percent,
                }
            else:
                model_to_thmz(
                    model,
                    str(thmz_path),
                    effective_par,
                    mesh_generator=gmsh_mesh_to_xml,
                )
                run_thmz(str(thmz_path), silent=silent)
                provenance = _verify_solver_outputs(thmz_path)
    except Exception as exc:
        status = "failed"
        error = str(exc)
        warnings.append(error)

    thmz_target = None
    thmz_relative_path = None
    if thmz_path.is_file():
        thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
        thmz_target = make_fairyfly_thmz_target(
            garden_id=garden_id,
            run_id=run_id,
            path=thmz_relative_path,
        )

    updated = {
        **existing,
        "status": status,
        "runtime_status": status,
        "error": error,
        "completed_at": utc_now_iso(),
        "thmz_target": thmz_target,
        "thmz_path": thmz_relative_path,
        "simulation_mode": provenance.get("mode") if provenance else existing.get("simulation_mode"),
        "solver_provenance": provenance,
        "mesh_convergence": mesh_convergence,
        "warnings": warnings,
    }
    _THERM_RUNS.upsert(garden_root_path, updated)


def _resolve_direct_thmz_source(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any] | None,
    thmz_path: str | None,
) -> Path | None:
    if thmz_target is not None:
        resolved, _, _ = _thmz_path_from_target(
            garden_root=garden_root,
            manifest=manifest,
            thmz_target=thmz_target,
        )
        return resolved
    if thmz_path:
        candidate = Path(thmz_path).expanduser()
        if candidate.is_absolute():
            if not candidate.is_file():
                raise FileNotFoundError(f"THMZ file not found: {thmz_path}")
            return candidate.resolve()
        return resolve_existing_garden_path(
            garden_root, thmz_path, kind="file", label="THERM THMZ file"
        )
    return None


def start_fairyfly_therm_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    thmz_target: dict[str, Any] | None = None,
    thmz_path: str | None = None,
    run_id: str | None = None,
    silent: bool = True,
    export_only: bool = False,
    include_mesh: bool = False,
    name: str | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start an async Fairyfly pyHygroThermFEM run (or export THMZ only) and persist the Garden run ledger."""
    if export_only:
        return write_fairyfly_model_to_thmz(
            garden_root=garden_root,
            model_target=model_target,
            run_id=run_id,
            name=name,
            simulation_parameter=simulation_parameter,
            include_mesh=include_mesh,
        )
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    source_thmz = _resolve_direct_thmz_source(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        thmz_path=thmz_path,
    )
    resolved_model_target: dict[str, Any] | None = None
    model_path: str | None = None
    if source_thmz is None or model_target is not None:
        manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
        model_path = resolved_model_target.get("path")

    normalized_run_id = _THERM_RUNS.normalize_run_id(run_id)
    run_dir = _THERM_RUNS.run_dir(garden_root_path, normalized_run_id)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    target = make_fairyfly_therm_run_target(manifest.garden_id, normalized_run_id)
    sim_par = _coerce_simulation_parameter(simulation_parameter)
    sim_par_dict = sim_par.to_dict() if sim_par is not None else None
    engine = therm_engine_config()
    started_at = utc_now_iso()

    if not engine.get("available"):
        disabled_reason = str(engine.get("disabled_reason") or "hygrothermfem_unavailable")
        record = {
            "run_id": normalized_run_id,
            "target": target,
            "recipe": FAIRYFLY_THERM_RECIPE,
            "status": "blocked",
            "runtime_status": "blocked",
            "created_at": started_at,
            "completed_at": utc_now_iso(),
            "model_target": resolved_model_target,
            "model_path": model_path,
            "source_thmz_path": str(source_thmz) if source_thmz else None,
            "run_folder": run_folder,
            "simulation_parameter": sim_par_dict,
            "engine": engine,
            "disabled_reason": disabled_reason,
            "warnings": [f"THERM/pyHygroThermFEM runtime unavailable: {disabled_reason}"],
        }
        _THERM_RUNS.upsert(garden_root_path, record)
        return _run_response(
            garden_root=garden_root_path,
            manifest=manifest,
            record=record,
            message="Fairyfly THERM run blocked because pyHygroThermFEM runtime is unavailable.",
            report_status="blocked",
        )

    record = {
        "run_id": normalized_run_id,
        "target": target,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "status": "running",
        "runtime_status": "running",
        "worker_pid": None,
        "error": None,
        "created_at": started_at,
        "completed_at": None,
        "model_target": resolved_model_target,
        "model_path": model_path,
        "source_thmz_path": str(source_thmz) if source_thmz else None,
        "run_folder": run_folder,
        "thmz_target": None,
        "thmz_path": None,
        "simulation_parameter": sim_par_dict,
        "simulation_mode": None,
        "solver_provenance": None,
        "mesh_convergence": None,
        "engine": engine,
        "warnings": [],
    }
    _THERM_RUNS.upsert(garden_root_path, record)

    proc = submit_worker_process(
        garden_root=garden_root_path,
        run_dir=run_dir,
        worker_module="garden.fairyfly.therm:_run_therm_worker",
        request={
            "garden_root": str(garden_root_path),
            "run_id": normalized_run_id,
            "garden_id": manifest.garden_id,
            "model_target": resolved_model_target,
            "thmz_source_path": str(source_thmz) if source_thmz else None,
            "silent": silent,
            "simulation_parameter": sim_par_dict,
        },
        cwd=garden_root_path,
        environment=os.environ.copy(),
    )
    latest = dict(_THERM_RUNS.get(garden_root_path, normalized_run_id) or record)
    latest["worker_pid"] = getattr(proc, "pid", None)
    _THERM_RUNS.upsert(garden_root_path, latest)
    record = latest

    if wait_seconds is not None and float(wait_seconds) > 0:
        deadline = time.monotonic() + min(float(wait_seconds), 300.0)
        sleep_step = max(min(float(poll_interval), 5.0), 0.1)
        while time.monotonic() < deadline:
            current = _THERM_RUNS.require(garden_root_path, normalized_run_id)
            if current.get("status") not in {"running", "queued"}:
                record = current
                break
            time.sleep(min(sleep_step, max(deadline - time.monotonic(), 0.05)))
        record = _THERM_RUNS.require(garden_root_path, normalized_run_id)

    final_status = str(record.get("status") or "running")
    if final_status == "completed":
        message = "Fairyfly THERM run completed."
        report_status = "ok"
    elif final_status == "failed":
        message = "Fairyfly THERM run failed; see therm.log and warnings."
        report_status = "error"
    else:
        message = f"Fairyfly THERM run started ({normalized_run_id}); poll GD_Poll_Run until complete."
        report_status = "ok"

    return _run_response(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=message,
        report_status=report_status,
    )


def get_fairyfly_therm_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Get one Fairyfly THERM run record."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _THERM_RUNS.resolve_run_id(run_target, run_id)
    record = _THERM_RUNS.public_run(_THERM_RUNS.require(garden_root_path, resolved_run_id))
    return _run_response(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Fairyfly THERM run returned: {resolved_run_id}",
        report_status="ok" if record.get("status") != "blocked" else "blocked",
    )


def list_fairyfly_therm_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List Fairyfly THERM runs registered in a Garden."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    records = [_THERM_RUNS.public_run(record) for record in _THERM_RUNS.list(garden_root_path)]
    if status:
        records = [record for record in records if record.get("status") == status]
    return {
        "matches": records,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(records),
            "status": status or "all",
        },
        "report": make_report(status="ok", message=f"Found {len(records)} Fairyfly THERM run(s)."),
    }


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"value_count": 0, "minimum": None, "maximum": None, "mean": None}
    return {
        "value_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": fmean(values),
    }


def _normalize_data_type(data_type: str) -> tuple[str, str]:
    key = data_type.strip().lower().replace("-", "_").replace(" ", "_")
    attr = _DATA_TYPE_ATTRS.get(key)
    if attr is None:
        raise ValueError(
            "data_type must be temperature, heat_flux, heat_flux_vectors, humidity, "
            "water_content, u_factor, condensation_risk, psi_factor, transient_summary, "
            "or transient_series."
        )
    return _DATA_TYPE_NAMES[attr], attr


def _read_archive_member(archive: zipfile.ZipFile, member_name: str) -> bytes:
    """Read an archive member tolerating slash or backslash separators."""
    try:
        return archive.read(member_name)
    except KeyError:
        alt = member_name.replace("/", "\\")
        return archive.read(alt)


def _active_mesh_node_ids(archive: zipfile.ZipFile) -> list[int]:
    """Return 1-based Mesh.xml node indices ordered identically to THMZResult.mesh.vertices."""
    try:
        mesh_root = ET.fromstring(archive.read("Mesh.xml"))
    except (KeyError, ET.ParseError):
        return []
    case = mesh_root.find("Case")
    if case is None:
        return []
    node_ids = [
        int(node.findtext("index"))  # type: ignore[arg-type]
        for node in case.findall("Nodes/Node")
        if node.findtext("index") is not None
    ]
    used_indices = {
        int(child.text)  # type: ignore[arg-type]
        for elem in case.findall("Elements/Element")
        for child in elem
        if child.tag.startswith("node") and child.text is not None
    }
    if not used_indices:
        return node_ids
    return [nid for idx, nid in enumerate(node_ids) if idx in used_indices]


def _resolve_timestep_index(count: int, timestep_index: int | None) -> int:
    if count <= 0:
        raise ValueError("Transient series contains zero rows.")
    if timestep_index is None:
        return count - 1
    idx = int(timestep_index)
    if idx < 0:
        idx += count
    if not 0 <= idx < count:
        raise ValueError(
            f"timestep_index {timestep_index} out of range for {count} transient frame(s)."
        )
    return idx


def _read_transient_node_field(
    thmz_path: Path,
    normalized_data_type: str,
    timestep_index: int | None,
) -> tuple[list[float], dict[str, Any]] | None:
    """Extract a node-aligned scalar field from transient results/*.csv."""
    member = _TRANSIENT_NODE_FIELD_MAP.get(normalized_data_type)
    if member is None:
        return None
    with zipfile.ZipFile(thmz_path, "r") as archive:
        try:
            csv_bytes = _read_archive_member(archive, member)
        except KeyError:
            return None
        series = read_transient_series(csv_bytes)
        times = list(series.get("times") or ())
        if not times:
            return None
        idx = _resolve_timestep_index(len(times), timestep_index)
        entities = tuple(series["entities"])
        row = list(series["values"][idx])
        active_ids = _active_mesh_node_ids(archive)
        if active_ids:
            by_id = {eid: float(val) for eid, val in zip(entities, row)}
            aligned = [by_id[nid] for nid in active_ids if nid in by_id]
            values = aligned if len(aligned) == len(active_ids) else [float(v) for v in row]
        else:
            values = [float(v) for v in row]
        meta = {
            "source_layout": "transient",
            "timestep_index": idx,
            "time_s": float(times[idx]),
            "step_count": len(times),
        }
        return values, meta


def _unit_scale_to_meters(unit: str) -> float:
    scale = _LENGTH_TO_METERS.get(str(unit or "").strip().lower())
    if scale is None:
        raise ValueError(
            f"Unsupported length unit {unit!r}. Use Meters, Millimeters, Centimeters, Feet, or Inches."
        )
    return scale


def _thmz_path_from_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any],
) -> tuple[Path, str, dict[str, Any]]:
    if thmz_target.get("target_type") != FAIRYFLY_THMZ_TARGET_TYPE:
        raise ValueError("thmz_target must have target_type 'fairyfly_thmz'.")
    if thmz_target.get("garden_id") != manifest.garden_id:
        raise ValueError("thmz_target belongs to a different Garden.")
    path_value = thmz_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("thmz_target requires a Garden-relative path.")
    path = resolve_existing_garden_path(garden_root, path_value, kind="file", label="THERM THMZ file")
    run_id = str(thmz_target.get("run_id") or path.stem)
    return path, run_id, dict(thmz_target)


def _resolve_thmz_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any] | None,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> tuple[Path, str, dict[str, Any] | None]:
    if thmz_target is not None:
        return _thmz_path_from_target(
            garden_root=garden_root, manifest=manifest, thmz_target=thmz_target
        )
    if run_target is None and not run_id:
        raise ValueError("Provide thmz_target, run_target, or run_id.")
    resolved_run_id = _THERM_RUNS.resolve_run_id(run_target, run_id)
    record = _THERM_RUNS.require(garden_root, resolved_run_id)
    thmz_ref = record.get("thmz_target")
    if not isinstance(thmz_ref, dict):
        raise ValueError("Fairyfly run record requires a thmz_target.")
    path, _, resolved_target = _thmz_path_from_target(
        garden_root=garden_root, manifest=manifest, thmz_target=thmz_ref
    )
    return path, resolved_run_id, resolved_target


def _numeric_values(values: Any) -> list[float]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        values = list(values)
    return [float(value) for value in values if value is not None]


def _write_result_payload(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_id: str,
    data_type: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    output_dir = (garden_root / RESULTS_DIR).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{run_id}_{data_type}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    relative_path = to_posix_relative(path, garden_root)
    source = {"run_id": run_id, "data_type": data_type, "thmz_path": payload.get("thmz_path")}
    artifact = _register_artifact(
        manifest,
        artifact_type=FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE,
        name=f"{run_id}_{data_type}",
        path=relative_path,
        source=source,
    )
    manifest.write(garden_root)
    target = make_fairyfly_therm_result_target(
        garden_id=manifest.garden_id,
        run_id=run_id,
        data_type=data_type,
        path=relative_path,
    )
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE,
        artifact_path=relative_path,
        absolute_path=str(path),
        source=source,
    )
    return target, artifact, receipt


def read_fairyfly_therm_result(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    data_type: str = "temperature",
    timestep_index: int | None = None,
    include_values: bool = False,
) -> dict[str, Any]:
    """Read temperature, heat-flux, humidity, or water-content results from a THMZ file."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_data_type, attr = _normalize_data_type(data_type)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    thmz_result = THMZResult(str(thmz_path))
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)

    if normalized_data_type == "heat_flux_vectors":
        raw_vectors = list(getattr(thmz_result, attr) or ())
        vectors = [[float(vec.x), float(vec.y)] for vec in raw_vectors]
        magnitudes = [float(vec.magnitude) for vec in raw_vectors]
        xs = [float(vec.x) for vec in raw_vectors]
        ys = [float(vec.y) for vec in raw_vectors]
        stats = {
            **_stats(magnitudes),
            "vector_count": len(vectors),
            "mean_x": fmean(xs) if xs else None,
            "mean_y": fmean(ys) if ys else None,
        }
        if not vectors:
            return {
                "summary_view": {
                    "garden_target": manifest.target(),
                    "status": "no_results",
                    "run_id": resolved_run_id,
                    "data_type": normalized_data_type,
                    "thmz_target": resolved_thmz_target,
                    "thmz_path": thmz_relative_path,
                    **stats,
                },
                "report": make_report(
                    status="warning",
                    message=(
                        "THERM heat-flux vector results were not found in the THMZ. "
                        "Run steady-state THERM first and then read the completed result."
                    ),
                    warnings=["THERM mesh/results are missing from the THMZ."],
                ),
            }
        payload = {
            "run_id": resolved_run_id,
            "data_type": normalized_data_type,
            "thmz_path": thmz_relative_path,
            "statistics": stats,
            "vectors": vectors,
            "magnitudes": magnitudes,
        }
        target, artifact, receipt = _write_result_payload(
            garden_root=garden_root_path,
            manifest=manifest,
            run_id=resolved_run_id,
            data_type=normalized_data_type,
            payload=payload,
        )
        response: dict[str, Any] = {
            "target": target,
            "therm_result_target": target,
            "artifact": artifact,
            "artifact_receipt": receipt,
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "ok",
                "run_id": resolved_run_id,
                "data_type": normalized_data_type,
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
                "therm_result_target": target,
                **stats,
            },
            "report": make_report(
                status="ok",
                message=f"Fairyfly THERM {normalized_data_type} result returned.",
            ),
        }
        if include_values:
            response["vectors"] = vectors
            response["values"] = magnitudes
        return response

    values = _numeric_values(getattr(thmz_result, attr))
    transient_meta: dict[str, Any] = {}
    if not values:
        transient_res = _read_transient_node_field(thmz_path, normalized_data_type, timestep_index)
        if transient_res is not None:
            values, transient_meta = transient_res
    stats = _stats(values)
    if not values:
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "no_results",
                "run_id": resolved_run_id,
                "data_type": normalized_data_type,
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
                **stats,
            },
            "report": make_report(
                status="warning",
                message=(
                    f"THERM {normalized_data_type} values were not found in the THMZ. "
                    "Run pyHygroThermFEM first and then read the completed result."
                ),
                warnings=[f"THERM {normalized_data_type} results are missing from the THMZ."],
            ),
        }

    payload = {
        "run_id": resolved_run_id,
        "data_type": normalized_data_type,
        "thmz_path": thmz_relative_path,
        "statistics": stats,
        **transient_meta,
        "values": values,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type=normalized_data_type,
        payload=payload,
    )
    response = {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": normalized_data_type,
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            **transient_meta,
            **stats,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly THERM {normalized_data_type} result returned.",
        ),
    }
    if include_values:
        response["values"] = values
    return response


def _point_to_segment_distance_3d(pt: Any, seg: Any) -> float:
    ax, ay, az = float(seg.p.x), float(seg.p.y), float(seg.p.z)
    vx, vy, vz = float(seg.v.x), float(seg.v.y), float(seg.v.z)
    px, py, pz = float(pt.x) - ax, float(pt.y) - ay, float(pt.z) - az
    len_sq = vx * vx + vy * vy + vz * vz
    if len_sq <= 1e-18:
        return (px * px + py * py + pz * pz) ** 0.5
    t = max(0.0, min(1.0, (px * vx + py * vy + pz * vz) / len_sq))
    dx = px - t * vx
    dy = py - t * vy
    dz = pz - t * vz
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _load_optional_model_for_run(
    *,
    garden_root: Path,
    model_target: dict[str, Any] | None,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> Any | None:
    resolved_target = model_target
    if resolved_target is None and (run_target is not None or run_id):
        resolved_run_id = _THERM_RUNS.resolve_run_id(run_target, run_id)
        record = _THERM_RUNS.require(garden_root, resolved_run_id)
        if isinstance(record.get("model_target"), dict):
            resolved_target = record["model_target"]
    if resolved_target is None:
        return None
    try:
        return load_fairyfly_model(garden_root, resolved_target)
    except Exception:
        return None


def read_fairyfly_condensation_risk(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    model_target: dict[str, Any] | None = None,
    interior_temp_c: float | None = None,
    interior_rh: float | None = None,
    exterior_temp_c: float | None = None,
    interior_surface_temp_c: float | None = None,
    timestep_index: int | None = None,
) -> dict[str, Any]:
    """Evaluate condensation risk (min surface temp, dew point, f_Rsi, RH margin) from THERM."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    model = _load_optional_model_for_run(
        garden_root=garden_root_path,
        model_target=model_target,
        run_target=run_target,
        run_id=run_id,
    )

    boundary_temps: list[tuple[Any, float]] = []
    if model is not None:
        for boundary in getattr(model, "boundaries", ()) or ():
            cond = getattr(getattr(boundary, "properties", None), "therm", None)
            cond_obj = getattr(cond, "condition", None) if cond is not None else None
            temp = getattr(cond_obj, "temperature", None)
            if temp is None and getattr(cond_obj, "timesteps", None):
                first_step = cond_obj.timesteps[min(cond_obj.timesteps)]
                temp = first_step.get("temperature") or first_step.get("surface_temperature")
            if temp is not None:
                boundary_temps.append((boundary, float(temp)))

    resolved_int_temp = interior_temp_c
    resolved_ext_temp = exterior_temp_c
    resolved_rh = interior_rh
    warmest_boundary: Any = None
    if boundary_temps:
        warmest_boundary, warmest_temp = max(boundary_temps, key=lambda item: item[1])
        coolest_temp = min(item[1] for item in boundary_temps)
        if resolved_int_temp is None:
            resolved_int_temp = warmest_temp
        if resolved_ext_temp is None:
            resolved_ext_temp = coolest_temp
        if resolved_rh is None:
            warm_cond = warmest_boundary.properties.therm.condition
            warm_rh = getattr(warm_cond, "relative_humidity", None)
            if warm_rh is None and getattr(warm_cond, "timesteps", None):
                warm_rh = warm_cond.timesteps[min(warm_cond.timesteps)].get("humidity")
            if warm_rh is not None:
                resolved_rh = float(warm_rh)

    if resolved_int_temp is None or resolved_ext_temp is None:
        raise ValueError(
            "interior_temp_c and exterior_temp_c are required when they cannot be inferred "
            "from the Fairyfly model boundaries."
        )
    if resolved_rh is None:
        resolved_rh = 50.0
    rh_pct = float(resolved_rh) * 100.0 if 0.0 <= float(resolved_rh) <= 1.0 else float(resolved_rh)
    if rh_pct <= 0.0 or rh_pct > 100.0:
        raise ValueError("interior_rh must be in (0, 1] (fraction) or (0, 100] (%).")

    surface_temp_source = "explicit"
    if interior_surface_temp_c is not None:
        min_surface_temp = float(interior_surface_temp_c)
    else:
        thmz_result = THMZResult(str(thmz_path))
        temps = _numeric_values(thmz_result.temperatures)
        if not temps:
            transient_res = _read_transient_node_field(thmz_path, "temperature", timestep_index)
            if transient_res is not None:
                temps, _ = transient_res
        if not temps:
            return {
                "summary_view": {
                    "garden_target": manifest.target(),
                    "status": "no_results",
                    "run_id": resolved_run_id,
                    "data_type": "condensation_risk",
                    "thmz_target": resolved_thmz_target,
                    "thmz_path": thmz_relative_path,
                },
                "report": make_report(
                    status="warning",
                    message="THERM temperature results were not found in the THMZ.",
                    warnings=["THERM mesh/results are missing from the THMZ."],
                ),
            }

        matched_temps: list[float] = []
        if model is not None and thmz_result.mesh is not None and len(thmz_result.mesh.vertices) == len(temps):
            model_to_mm = _unit_scale_to_meters(str(getattr(model, "units", "Millimeters"))) / 0.001
            interior_boundaries = [
                b for b, temp in boundary_temps if abs(temp - float(resolved_int_temp)) <= 0.25
            ]
            if interior_boundaries:
                segs = [seg for b in interior_boundaries for seg in b.geometry]
                if model_to_mm != 1.0:
                    from ladybug_geometry.geometry3d.line import LineSegment3D
                    from ladybug_geometry.geometry3d.pointvector import Point3D

                    segs = [
                        LineSegment3D.from_end_points(
                            Point3D(s.p.x * model_to_mm, s.p.y * model_to_mm, s.p.z * model_to_mm),
                            Point3D(s.p2.x * model_to_mm, s.p2.y * model_to_mm, s.p2.z * model_to_mm),
                        )
                        for s in segs
                    ]
                dist_tol = max(float(getattr(model, "tolerance", 0.01) or 0.01) * model_to_mm * 10.0, 1.0)
                for vertex, temp_val in zip(thmz_result.mesh.vertices, temps):
                    if min((_point_to_segment_distance_3d(vertex, seg) for seg in segs), default=1e9) <= dist_tol:
                        matched_temps.append(float(temp_val))
        if matched_temps:
            min_surface_temp = min(matched_temps)
            surface_temp_source = "interior_boundary_vertices"
        else:
            min_surface_temp = min(temps)
            surface_temp_source = "mesh_minimum"

    t_int = float(resolved_int_temp)
    t_ext = float(resolved_ext_temp)
    dew_point_c = float(dew_point_from_db_rh(t_int, rh_pct))
    max_safe_rh_pct = (
        100.0
        if min_surface_temp >= t_int
        else min(100.0, float(rel_humid_from_db_dpt(t_int, min_surface_temp)))
    )
    rh_margin_pct = max_safe_rh_pct - rh_pct
    temperature_margin_c = min_surface_temp - dew_point_c
    condensation_risk = bool(min_surface_temp <= dew_point_c)
    delta_t = t_int - t_ext
    f_rsi = (min_surface_temp - t_ext) / delta_t if abs(delta_t) > 1e-9 else None

    payload = {
        "run_id": resolved_run_id,
        "data_type": "condensation_risk",
        "thmz_path": thmz_relative_path,
        "min_interior_surface_temp_c": round(min_surface_temp, 4),
        "surface_temp_source": surface_temp_source,
        "interior_temp_c": round(t_int, 4),
        "exterior_temp_c": round(t_ext, 4),
        "interior_rh_pct": round(rh_pct, 4),
        "dew_point_c": round(dew_point_c, 4),
        "temperature_margin_c": round(temperature_margin_c, 4),
        "max_safe_rh_pct": round(max_safe_rh_pct, 4),
        "rh_margin_pct": round(rh_margin_pct, 4),
        "f_rsi": round(f_rsi, 6) if f_rsi is not None else None,
        "condensation_risk": condensation_risk,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type="condensation_risk",
        payload=payload,
    )
    return {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "condensation_risk_analysis": payload,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "condensation_risk",
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            **payload,
        },
        "report": make_report(
            status="warning" if condensation_risk else "ok",
            message=(
                f"Condensation risk detected (T_surf={min_surface_temp:.2f}C <= T_dew={dew_point_c:.2f}C)."
                if condensation_risk
                else f"No condensation risk (T_surf={min_surface_temp:.2f}C > T_dew={dew_point_c:.2f}C)."
            ),
            warnings=(
                [f"Minimum surface temperature {min_surface_temp:.2f}C is below dew point {dew_point_c:.2f}C."]
                if condensation_risk
                else []
            ),
        ),
    }


def read_fairyfly_psi_factor(
    *,
    garden_root: str,
    clear_field_u_values: list[dict[str, Any]],
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    u_factor_name: str | None = None,
    projection: str = "total",
    l_2d_w_per_mk: float | None = None,
    length_unit: str = "Meters",
    therm_length_unit: str = "Millimeters",
) -> dict[str, Any]:
    """Compute thermal bridge Psi-factor (Psi = L_2D - sum(U_i * l_i)) from THERM U-factor."""
    if not isinstance(clear_field_u_values, list) or not clear_field_u_values:
        raise ValueError("clear_field_u_values must be a non-empty list of {u_value, length} dicts.")
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    cf_scale = _unit_scale_to_meters(length_unit)
    therm_scale = _unit_scale_to_meters(therm_length_unit)

    selected_tag: dict[str, Any] | None = None
    resolved_l2d = l_2d_w_per_mk
    if resolved_l2d is None:
        result = THMZResult(str(thmz_path))
        u_factors = list(result.u_factors or ())
        if not u_factors:
            return {
                "summary_view": {
                    "garden_target": manifest.target(),
                    "status": "no_results",
                    "run_id": resolved_run_id,
                    "data_type": "psi_factor",
                    "thmz_target": resolved_thmz_target,
                    "thmz_path": thmz_relative_path,
                },
                "report": make_report(
                    status="warning",
                    message="THERM U-Factor results were not found in the THMZ for Psi calculation.",
                    warnings=["THERM U-Factor results are missing from the THMZ."],
                ),
            }
        chosen = u_factors[0]
        if u_factor_name is not None:
            matches = [item for item in u_factors if item.name == u_factor_name]
            if not matches:
                raise KeyError(f"THERM U-Factor tag {u_factor_name!r} not found in {thmz_relative_path}.")
            chosen = matches[0]
        proj_map = {
            "total": ("total_u_factor", "total_length"),
            "projected_x": ("projected_x_u_factor", "projected_x_length"),
            "projected_y": ("projected_y_u_factor", "projected_y_length"),
            "projected_in_glass_plane": ("projected_in_glass_plane_u_factor", "projected_in_glass_plane_length"),
            "custom_rotation": ("custom_rotation_u_factor", "custom_rotation_length"),
        }
        proj_key = projection.strip().lower()
        candidates = (
            [proj_key, "total", "projected_x", "projected_y"]
            if proj_key == "auto"
            else [proj_key]
        )
        u_attr: str | None = None
        len_attr: str | None = None
        used_proj: str | None = None
        for key in candidates:
            if key not in proj_map:
                raise ValueError(f"Unsupported U-Factor projection {projection!r}.")
            ua, la = proj_map[key]
            u_val = getattr(chosen, ua, None)
            l_val = getattr(chosen, la, None)
            if u_val is not None and l_val:
                u_attr, len_attr, used_proj = ua, la, key
                break
        if u_attr is None or len_attr is None:
            raise ValueError(f"U-Factor tag {chosen.name!r} has no non-zero value for projection {projection!r}.")
        u_val = float(getattr(chosen, u_attr))
        raw_len = float(getattr(chosen, len_attr))
        length_m = raw_len * therm_scale
        resolved_l2d = u_val * length_m
        selected_tag = {
            "name": chosen.name,
            "projection": used_proj,
            "u_factor_w_per_m2k": u_val,
            "length_raw": raw_len,
            "length_m": length_m,
            "delta_temperature": getattr(chosen, "delta_temperature", None),
            "heat_flux": getattr(chosen, "heat_flux", None),
        }

    components: list[dict[str, Any]] = []
    clear_field_sum = 0.0
    for idx, item in enumerate(clear_field_u_values):
        if not isinstance(item, dict) or item.get("u_value") is None or item.get("length") is None:
            raise ValueError(f"clear_field_u_values[{idx}] must contain 'u_value' and 'length'.")
        u_i = float(item["u_value"])
        l_i_m = float(item["length"]) * cf_scale
        contrib = u_i * l_i_m
        clear_field_sum += contrib
        components.append(
            {
                "name": item.get("name") or f"segment_{idx + 1}",
                "u_value_w_per_m2k": u_i,
                "length_m": l_i_m,
                "u_times_l_w_per_mk": round(contrib, 6),
            }
        )

    psi_val = float(resolved_l2d) - clear_field_sum
    payload = {
        "run_id": resolved_run_id,
        "data_type": "psi_factor",
        "thmz_path": thmz_relative_path,
        "l_2d_w_per_mk": round(float(resolved_l2d), 6),
        "clear_field_sum_w_per_mk": round(clear_field_sum, 6),
        "psi_w_per_mk": round(psi_val, 6),
        "u_factor_tag": selected_tag,
        "components": components,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type="psi_factor",
        payload=payload,
    )
    return {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "psi_factor": payload,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "psi_factor",
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            "psi_w_per_mk": payload["psi_w_per_mk"],
            "l_2d_w_per_mk": payload["l_2d_w_per_mk"],
            "clear_field_sum_w_per_mk": payload["clear_field_sum_w_per_mk"],
            "u_factor_tag": selected_tag,
        },
        "report": make_report(
            status="ok",
            message=f"Computed Psi-factor {payload['psi_w_per_mk']:.4f} W/(m-K) for {resolved_run_id}.",
        ),
    }


def read_fairyfly_u_factor_result(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read U-Factor result summaries from a THERM THMZ file."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    result = THMZResult(str(thmz_path))
    u_factors = [
        {field: getattr(item, field, None) for field in _U_FACTOR_FIELDS}
        for item in (result.u_factors or [])
    ]
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    if not u_factors:
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "no_results",
                "run_id": resolved_run_id,
                "data_type": "u_factors",
                "result_count": 0,
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
            },
            "report": make_report(
                status="warning",
                message=(
                    "THERM U-Factor results were not found in the THMZ. "
                    "Confirm U-Factor tags and run THERM before reading results."
                ),
                warnings=["THERM U-Factor results are missing from the THMZ."],
            ),
        }

    payload = {
        "run_id": resolved_run_id,
        "data_type": "u_factors",
        "thmz_path": thmz_relative_path,
        "result_count": len(u_factors),
        "u_factors": u_factors,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type="u_factors",
        payload=payload,
    )
    target = make_fairyfly_u_factor_result_target(
        garden_id=manifest.garden_id,
        run_id=resolved_run_id,
        path=target["path"],
    )
    return {
        "target": target,
        "u_factor_result_target": target,
        "u_factors": u_factors,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "u_factors",
            "result_count": len(u_factors),
            "u_factor_result_target": target,
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly THERM U-Factor result returned for {resolved_run_id}.",
        ),
    }


def read_fairyfly_transient_summary(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read transient/hygrothermal summary statistics and geometry counts from a solved THMZ."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)

    provenance: dict[str, Any] | None = None
    geometry_counts: dict[str, int] | None = None
    field_summaries: dict[str, Any] = {}
    times_ref: list[float] = []

    with zipfile.ZipFile(thmz_path, "r") as archive:
        if "pyHygroTherm.json" in archive.namelist():
            provenance = json.loads(archive.read("pyHygroTherm.json").decode("utf-8"))
        try:
            geom_bytes = _read_archive_member(archive, TRANSIENT_RESULT_MEMBERS["geometry"])
            geom = read_geometry_xml(geom_bytes)
            geometry_counts = {
                "materials": len(geom.get("materials", ())),
                "nodes": len(geom.get("nodes", ())),
                "elements": len(geom.get("elements", ())),
                "material_polygons": len(geom.get("material_polygons", ())),
                "model_enclosure_nodes": len(geom.get("model_enclosure", ())),
            }
        except KeyError:
            pass

        for field_name, member_path in _TRANSIENT_SERIES_FIELDS:
            try:
                csv_bytes = _read_archive_member(archive, member_path)
            except KeyError:
                continue
            series = read_transient_series(csv_bytes)
            times = list(series.get("times") or ())
            if times and not times_ref:
                times_ref = [float(t) for t in times]
            entities = tuple(series.get("entities") or ())
            rows = list(series.get("values") or ())
            final_row = [float(v) for v in rows[-1]] if rows else []
            all_vals = [float(v) for row in rows for v in row]
            field_summaries[field_name] = {
                "member": member_path,
                "entity_count": len(entities),
                "step_count": len(times),
                "final_step": _stats(final_row),
                "overall_min": min(all_vals) if all_vals else None,
                "overall_max": max(all_vals) if all_vals else None,
            }

    if not field_summaries and geometry_counts is None:
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "no_results",
                "run_id": resolved_run_id,
                "data_type": "transient_summary",
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
            },
            "report": make_report(
                status="warning",
                message="Transient result tables were not found in the THMZ archive.",
                warnings=["transient results/ members are missing from the THMZ."],
            ),
        }

    payload = {
        "run_id": resolved_run_id,
        "data_type": "transient_summary",
        "thmz_path": thmz_relative_path,
        "simulation_mode": provenance.get("mode") if provenance else None,
        "solver_provenance": provenance,
        "step_count": len(times_ref),
        "start_time_s": times_ref[0] if times_ref else None,
        "end_time_s": times_ref[-1] if times_ref else None,
        "geometry_counts": geometry_counts,
        "fields": field_summaries,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type="transient_summary",
        payload=payload,
    )
    return {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "transient_summary": payload,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "transient_summary",
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            "simulation_mode": payload["simulation_mode"],
            "step_count": payload["step_count"],
            "start_time_s": payload["start_time_s"],
            "end_time_s": payload["end_time_s"],
            "geometry_counts": geometry_counts,
            "available_fields": list(field_summaries),
            "fields": field_summaries,
        },
        "report": make_report(
            status="ok",
            message=f"Transient summary returned for {resolved_run_id} ({len(times_ref)} frame(s)).",
        ),
    }


def read_fairyfly_transient_series(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    field: str = "temperatures",
    entity_ids: list[int] | None = None,
    timestep_index: int | None = None,
    include_values: bool = False,
) -> dict[str, Any]:
    """Read transient time-series CSV values from transient results/*.csv."""
    norm_key = str(field or "temperatures").strip().lower().replace("-", "_").replace(" ", "_")
    resolved_field = _TRANSIENT_FIELD_ALIASES.get(norm_key)
    if resolved_field is None:
        raise ValueError(
            "Unsupported transient_series field {!r}. Choose from: {}.".format(
                field, ", ".join(k for k, _ in _TRANSIENT_SERIES_FIELDS)
            )
        )
    canon_field, member_path = resolved_field

    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)

    with zipfile.ZipFile(thmz_path, "r") as archive:
        try:
            csv_bytes = _read_archive_member(archive, member_path)
        except KeyError:
            return {
                "summary_view": {
                    "garden_target": manifest.target(),
                    "status": "no_results",
                    "run_id": resolved_run_id,
                    "data_type": "transient_series",
                    "field": canon_field,
                    "member": member_path,
                    "thmz_target": resolved_thmz_target,
                    "thmz_path": thmz_relative_path,
                },
                "report": make_report(
                    status="warning",
                    message=f"Transient table {member_path} was not found in the THMZ.",
                    warnings=[f"{member_path} is missing from the THMZ."],
                ),
            }

    series = read_transient_series(csv_bytes)
    all_entities = list(series.get("entities") or ())
    if entity_ids is not None:
        wanted = {int(eid) for eid in entity_ids}
        col_indices = [i for i, eid in enumerate(all_entities) if eid in wanted]
        if not col_indices:
            raise ValueError(
                f"None of requested entity_ids {sorted(wanted)} exist in {member_path}."
            )
        selected_entities = [all_entities[i] for i in col_indices]
    else:
        col_indices = list(range(len(all_entities)))
        selected_entities = all_entities

    raw_times = [float(t) for t in (series.get("times") or ())]
    raw_rows = list(series.get("values") or ())
    if timestep_index is not None:
        idx = _resolve_timestep_index(len(raw_times), timestep_index)
        times_out = [raw_times[idx]]
        values_out = [[float(raw_rows[idx][i]) for i in col_indices]]
    else:
        times_out = raw_times
        values_out = [[float(row[i]) for i in col_indices] for row in raw_rows]

    last_row_stats = _stats(values_out[-1] if values_out else [])
    all_vals = [v for row in values_out for v in row]
    overall_stats = _stats(all_vals)

    payload = {
        "run_id": resolved_run_id,
        "data_type": "transient_series",
        "field": canon_field,
        "member": member_path,
        "thmz_path": thmz_relative_path,
        "entities": selected_entities,
        "step_count": len(times_out),
        "times": times_out,
        "values": values_out,
        "final_step_statistics": last_row_stats,
        "overall_statistics": overall_stats,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type=f"transient_{canon_field}",
        payload=payload,
    )
    response: dict[str, Any] = {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "transient_series",
            "field": canon_field,
            "member": member_path,
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            "step_count": len(times_out),
            "entity_count": len(selected_entities),
            "entities_preview": selected_entities[:25],
            "start_time_s": times_out[0] if times_out else None,
            "end_time_s": times_out[-1] if times_out else None,
            "final_step_statistics": last_row_stats,
            "overall_statistics": overall_stats,
        },
        "report": make_report(
            status="ok",
            message=f"Transient {canon_field} series returned ({len(times_out)} frame(s), {len(selected_entities)} entity(ies)).",
        ),
    }
    if include_values:
        response["times"] = times_out
        response["entities"] = selected_entities
        response["values"] = values_out
    return response
