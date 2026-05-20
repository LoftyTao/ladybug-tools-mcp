"""File-based EnergyPlus/OpenStudio run services."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
from typing import Any

from honeybee_energy.result.eui import eui_from_sql
from honeybee_energy.run import run_idf, run_osw

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import to_posix_relative
from garden.run_energy.annual import (
    _normalize_run_id,
    _output_record,
    _outputs_map,
    _run_target,
    _upsert_record,
)
from garden.run_energy.config import WEATHER_TARGET_TYPE

IDF_FILE_RECIPE = "energyplus_idf"
OSM_FILE_RECIPE = "openstudio_osm"
IDF_OUTPUT_NAMES = ("idf", "sql", "zsz", "rdd", "html", "err", "eui")
OSM_OUTPUT_NAMES = ("osm", "idf", "sql", "zsz", "rdd", "html", "err", "eui")


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _unwrap_target(target: dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(target, dict) and isinstance(target.get("target"), dict):
        return target["target"]
    return target


def _resolve_garden_file(
    garden_root: Path,
    value: str,
    *,
    field_name: str,
    suffix: str,
) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = garden_root / path
    path = path.resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be inside the Garden root.") from exc
    if not path.is_file():
        raise ValueError(f"{field_name} must reference an existing file.")
    if path.suffix.lower() != suffix:
        raise ValueError(f"{field_name} must reference a {suffix} file.")
    return path


def _resolve_epw_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    required: bool,
) -> tuple[Path | None, dict[str, Any] | None]:
    weather_target = _unwrap_target(weather_target)
    if weather_target is not None and epw_path is not None:
        raise ValueError("Provide weather_target or epw_path, not both.")
    if weather_target is None and epw_path is None:
        if required:
            raise ValueError("Provide weather_target or epw_path.")
        return None, None
    if weather_target is not None:
        if weather_target.get("target_type") != WEATHER_TARGET_TYPE:
            raise ValueError("weather_target must be a Garden weather_file target.")
        garden_id = weather_target.get("garden_id")
        if garden_id and garden_id != manifest.garden_id:
            raise ValueError("weather_target belongs to a different Garden.")
        epw_value = weather_target.get("epw_path")
        if not isinstance(epw_value, str) or not epw_value:
            raise ValueError("weather_target requires an epw_path.")
        epw = _resolve_garden_file(
            garden_root,
            epw_value,
            field_name="weather_target.epw_path",
            suffix=".epw",
        )
        return epw, {"source_type": "weather_file", "weather_target": weather_target}
    epw = _resolve_garden_file(
        garden_root,
        str(epw_path),
        field_name="epw_path",
        suffix=".epw",
    )
    return epw, {"source_type": "epw_path", "epw_path": to_posix_relative(epw, garden_root)}


def _eui_output(sql_path: Path | None, run_dir: Path, *, absolute: bool = False) -> Path | None:
    if sql_path is None or not sql_path.is_file():
        return None
    try:
        eui = eui_from_sql(str(sql_path), absolute=absolute)
    except Exception:
        return None
    eui_path = run_dir / "eui.json"
    eui_path.write_text(
        json.dumps(eui, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return eui_path


def _write_workflow_osw(
    *,
    osm_path: Path,
    epw_path: Path,
) -> Path:
    workflow_path = osm_path.parent / "workflow.osw"
    payload = {
        "seed_file": str(osm_path),
        "weather_file": str(epw_path),
    }
    workflow_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return workflow_path


def _idf_run_input(idf_path: Path) -> Path:
    if idf_path.name.lower() == "in.idf":
        return idf_path
    run_dir = idf_path.parent / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_idf_path = run_dir / "in.idf"
    shutil.copyfile(idf_path, run_idf_path)
    return run_idf_path


def _energyplus_output_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "sql": run_dir / "eplusout.sql",
        "zsz": run_dir / "epluszsz.csv",
        "rdd": run_dir / "eplusout.rdd",
        "html": run_dir / "eplustbl.htm",
        "err": run_dir / "eplusout.err",
    }


def _existing_file(path: Path) -> Path | None:
    return path if path.is_file() else None


def _file_outputs(
    *,
    garden_root: Path,
    run_dir: Path,
    output_paths: dict[str, Path | None],
    output_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for name in output_names:
        value = output_paths.get(name)
        outputs.append(_output_record(garden_root, run_dir, name, value))
    return outputs


def _response(
    *,
    manifest: GardenManifest,
    record: dict[str, Any],
    warnings: list[str],
    completed_message: str,
    failed_message: str,
) -> dict[str, Any]:
    status = str(record.get("status"))
    target = record["target"]
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": record["run_id"],
            "status": status,
            "recipe": record["recipe"],
            "input_file_path": record.get("input_file_path"),
            "workflow_path": record.get("workflow_path"),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
        },
        "report": make_report(
            status="ok" if status == "completed" else "error",
            message=completed_message if status == "completed" else failed_message,
            warnings=warnings,
        ),
    }


def run_osm_file(
    *,
    garden_root: str,
    osm_path: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    run_id: str | None = None,
    silent: bool = True,
) -> dict[str, Any]:
    """Create a persistent workflow.osw beside an OSM and run it."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_osm = _resolve_garden_file(
        garden_root_path,
        osm_path,
        field_name="osm_path",
        suffix=".osm",
    )
    resolved_epw, weather_source = _resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
        required=True,
    )
    assert resolved_epw is not None
    workflow_path = _write_workflow_osw(osm_path=resolved_osm, epw_path=resolved_epw)
    run_dir = (resolved_osm.parent / "run").resolve()
    run_dir.relative_to(garden_root_path)

    resolved_run_id = _normalize_run_id(run_id)
    target = _run_target(
        manifest.garden_id,
        resolved_run_id,
        recipe=OSM_FILE_RECIPE,
    )
    warnings: list[str] = []
    started_at = utc_now_iso()
    status = "completed"
    osm_result: str | None = None
    idf_result: str | None = None
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            osm_result, idf_result = run_osw(
                str(workflow_path),
                measures_only=False,
                silent=silent,
            )
    except Exception as exc:
        status = "failed"
        warnings.append(str(exc))

    known_outputs = _energyplus_output_paths(run_dir)
    output_paths: dict[str, Path | None] = {
        "osm": _existing_file(Path(osm_result).resolve())
        if osm_result
        else _existing_file(run_dir / "in.osm"),
        "idf": _existing_file(Path(idf_result).resolve())
        if idf_result
        else _existing_file(run_dir / "in.idf"),
        **{name: _existing_file(path) for name, path in known_outputs.items()},
    }
    output_paths["eui"] = _eui_output(output_paths.get("sql"), run_dir)
    outputs = _file_outputs(
        garden_root=garden_root_path,
        run_dir=run_dir,
        output_paths=output_paths,
        output_names=OSM_OUTPUT_NAMES,
    )
    run_folder = to_posix_relative(run_dir, garden_root_path)
    record = {
        "run_id": resolved_run_id,
        "target": target,
        "recipe": OSM_FILE_RECIPE,
        "status": status,
        "created_at": started_at,
        "completed_at": utc_now_iso(),
        "input_file_path": to_posix_relative(resolved_osm, garden_root_path),
        "source_file_path": to_posix_relative(resolved_osm, garden_root_path),
        "workflow_path": to_posix_relative(workflow_path, garden_root_path),
        "weather_target": weather_target,
        "weather_source": weather_source,
        "epw_path": to_posix_relative(resolved_epw, garden_root_path),
        "run_folder": run_folder,
        "outputs": outputs,
        "warnings": warnings,
        "silent": silent,
    }
    _upsert_record(garden_root_path, record)
    return _response(
        manifest=manifest,
        record=record,
        warnings=warnings,
        completed_message="OSM file simulation completed.",
        failed_message="OSM file simulation failed; run record was saved.",
    )


def run_idf_file(
    *,
    garden_root: str,
    idf_path: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    expand_objects: bool = True,
    run_id: str | None = None,
    silent: bool = True,
) -> dict[str, Any]:
    """Run an edited IDF file using Grasshopper-style run folder behavior."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_idf = _resolve_garden_file(
        garden_root_path,
        idf_path,
        field_name="idf_path",
        suffix=".idf",
    )
    resolved_epw, weather_source = _resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
        required=False,
    )
    run_input = _idf_run_input(resolved_idf)
    run_dir = run_input.parent.resolve()
    run_dir.relative_to(garden_root_path)

    resolved_run_id = _normalize_run_id(run_id)
    target = _run_target(
        manifest.garden_id,
        resolved_run_id,
        recipe=IDF_FILE_RECIPE,
    )
    warnings: list[str] = []
    started_at = utc_now_iso()
    status = "completed"
    result_paths: tuple[str | None, str | None, str | None, str | None, str | None]
    result_paths = (None, None, None, None, None)
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result_paths = run_idf(
                str(run_input),
                str(resolved_epw) if resolved_epw is not None else None,
                expand_objects=expand_objects,
                silent=silent,
            )
    except Exception as exc:
        status = "failed"
        warnings.append(str(exc))

    sql, zsz, rdd, html, err = result_paths
    fallback_outputs = _energyplus_output_paths(run_dir)
    output_paths: dict[str, Path | None] = {
        "idf": _existing_file(run_input),
        "sql": _existing_file(Path(sql).resolve()) if sql else _existing_file(fallback_outputs["sql"]),
        "zsz": _existing_file(Path(zsz).resolve()) if zsz else _existing_file(fallback_outputs["zsz"]),
        "rdd": _existing_file(Path(rdd).resolve()) if rdd else _existing_file(fallback_outputs["rdd"]),
        "html": _existing_file(Path(html).resolve()) if html else _existing_file(fallback_outputs["html"]),
        "err": _existing_file(Path(err).resolve()) if err else _existing_file(fallback_outputs["err"]),
    }
    output_paths["eui"] = _eui_output(output_paths.get("sql"), run_dir)
    outputs = _file_outputs(
        garden_root=garden_root_path,
        run_dir=run_dir,
        output_paths=output_paths,
        output_names=IDF_OUTPUT_NAMES,
    )
    record = {
        "run_id": resolved_run_id,
        "target": target,
        "recipe": IDF_FILE_RECIPE,
        "status": status,
        "created_at": started_at,
        "completed_at": utc_now_iso(),
        "input_file_path": to_posix_relative(resolved_idf, garden_root_path),
        "source_file_path": to_posix_relative(resolved_idf, garden_root_path),
        "run_input_path": to_posix_relative(run_input, garden_root_path),
        "weather_target": weather_target,
        "weather_source": weather_source,
        "epw_path": (
            to_posix_relative(resolved_epw, garden_root_path)
            if resolved_epw is not None
            else None
        ),
        "run_folder": to_posix_relative(run_dir, garden_root_path),
        "outputs": outputs,
        "warnings": warnings,
        "expand_objects": expand_objects,
        "silent": silent,
    }
    _upsert_record(garden_root_path, record)
    return _response(
        manifest=manifest,
        record=record,
        warnings=warnings,
        completed_message="IDF file simulation completed.",
        failed_message="IDF file simulation failed; run record was saved.",
    )
